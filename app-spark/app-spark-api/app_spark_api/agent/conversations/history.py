# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""会话展示历史的读模型：把用户输入和 AG-UI 事件合成一条可翻页的流。

一页是若干个**完整的 run**，而不是固定条数的记录
------------------------------------------------

客户端回放历史用的是一个有状态的 reducer：``TOOL_CALL_ARGS`` / ``TOOL_CALL_RESULT`` 要靠
``TOOL_CALL_START`` 建出来的那一行才认得自己。把页切在一次工具调用中间，那次调用在界面上就永远
停在「正在执行」。而且 N 条事件跟「N 条看得见的内容」根本不是一回事：一轮回答里 RUN_STARTED、
STEP_STARTED、文本三件套、每次工具调用四个事件加起来，几十上百条很正常，按条数切页会出现「点了
加载更多但界面上什么都没多出来」。
"""

from __future__ import annotations

import base64
import binascii
from itertools import pairwise
from typing import TYPE_CHECKING

import attrs
from asgiref.sync import sync_to_async

from app_spark_api.agent.conversations import state
from app_spark_api.agent.conversations.entities import (
    ConversationHistoryRecord,
    UiEventRecord,
    UserMessageHistoryRecord,
)
from app_spark_api.agent.conversations.exceptions import InvalidHistoryCursorError
from app_spark_api.agent.conversations.models import ConversationUserMessage
from app_spark_api.agent.conversations.state_models import ConversationUiEvent

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from app_spark_api.agent.conversations.models import Conversation

# 一页默认覆盖几轮对话。刻意取小：``TOOL_CALL_ARGS`` 事件带着完整的工具参数，而 write_file 的参
# 数就是整份文件，所以一页的字节数远不是「条数 × 一条的平均大小」能估出来的。
DEFAULT_PAGE_RUNS = 5
MAX_PAGE_RUNS = 20

# 单页事件硬上限，防止一轮疯狂调工具的对话把一页撑爆。它按「一页的字节数」来定，和 `runs` 谁先到
# 算谁，所以调 `runs` 不需要跟着动它：撞上它只是这一页少给几轮，见 :func:`_resolve_page_start`。
MAX_PAGE_EVENTS = 1_000

# 游标的载荷就只是一个 int，但对外仍然编成不透明字符串：位置键怎么构成是这一侧的实现细节，哪天
# 改了切页方式（比如页边界不再落在 run 起点）可以原地替换，而暴露出去的 `before_seq` 就是契约
# 了。前缀带版本号，是为了换格式之后旧游标会明确报错，而不是被当成新格式误读出一个位置。
_CURSOR_VERSION = "h1"


@attrs.frozen
class HistoryPage:
    """一页展示历史，以及取更早一页需要的东西。

    :param records: 本页记录，按对话**正序**排列——客户端的 reducer 就是顺着喂的。翻页是往更早
        的方向走，但页内始终正序。
    :param next_cursor: 取更早一页时带上的游标；``None`` 表示已经到了会话开头。
    :param last_seq: AG-UI 事件频道当前的最后一个游标。一并给出来，客户端就能直接拿它当「已经
        看到哪」的水位去走 ui-events 正向追赶，不必为一个数字再发一次状态查询，也就没有两次请求
        之间的竞态。
    """

    records: list[ConversationHistoryRecord]
    next_cursor: str | None
    last_seq: int


def encode_cursor(start_seq: int) -> str:
    """把一页的起始 seq 编成对外的游标。

    :param start_seq: 该页最早一条 UI event 的 seq。
    :return: URL 安全的不透明游标。
    """
    return base64.urlsafe_b64encode(f"{_CURSOR_VERSION}:{start_seq}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> int:
    """把游标解回它携带的起始 seq。

    :param cursor: :func:`encode_cursor` 签发过的游标。
    :return: 该游标指向的 seq，读取时作为「只要比它更早的」上界。
    :raises InvalidHistoryCursorError: 游标不是本服务签发的，或者版本已经不认了。
    """
    try:
        # padding 的 `=` 在 URL 里不好看，签发时去掉了，这里按长度补回去再解。
        decoded = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidHistoryCursorError(cursor) from exc

    version, _, raw = decoded.partition(":")
    # `isascii` 和 `isdigit` 都要：后者对 '²' 之类的字符也为真，而 `int()` 并不认它们。
    if version != _CURSOR_VERSION or not (raw.isascii() and raw.isdigit()):
        raise InvalidHistoryCursorError(cursor)
    return int(raw)


def read_page(
    conversation: Conversation,
    *,
    before_seq: int | None = None,
    runs: int = DEFAULT_PAGE_RUNS,
) -> HistoryPage:
    """读一页展示历史，从最新的一页开始往更早的方向翻。

    不会启动 Runtime，也适用于已结束的会话：读的全是本服务自己的表。

    用法——第一页不带游标，之后一直用上一页的 ``next_cursor``，直到它为 ``None``::

        page = read_page(conversation)
        while page.next_cursor:
            page = read_page(conversation, before_seq=decode_cursor(page.next_cursor))

    这个循环一定会停：签发出去的游标严格递减（下一页的起点取自 ``seq < before_seq`` 的事件，所以
    必然更小），读到会话开头时 ``next_cursor`` 就是 ``None``，永远不会原地签发同一个游标。

    :param conversation: 已通过调用方权限检查的会话。
    :param before_seq: 只要位置比它更早的记录，也就是上一页的起始 seq；``None`` 表示读最新一页。
    :param runs: 本页覆盖几轮对话。撞上 :data:`MAX_PAGE_EVENTS` 时会不足这个数。
    :return: 本页记录、取更早一页的游标，以及事件频道当前的游标。
    """
    events: QuerySet[ConversationUiEvent] = ConversationUiEvent.objects.filter(conversation=conversation)
    messages: QuerySet[ConversationUserMessage] = ConversationUserMessage.objects.filter(conversation=conversation)
    if before_seq is not None:
        events = events.filter(seq__lt=before_seq)
        # 挂在 `before_seq - 1` 上的那些输入是上一页最早那一轮的开头，已经随上一页发出去了。
        messages = messages.filter(after_seq__lt=before_seq - 1)

    start_seq = _resolve_page_start(events, runs=runs)
    page_events = list(events.filter(seq__gte=start_seq).order_by("seq"))
    # 下界取 `start_seq - 1` 那一组输入的**整组之前**，而不是 `start_seq` 本身：发起这一轮的用户
    # 输入挂在上一轮最后一个事件后面，它和这一轮在界面上是同一个气泡对，不能被分到两页去。
    page_messages = list(messages.filter(after_seq__gte=max(start_seq - 1, 0)).order_by("after_seq", "id"))

    return HistoryPage(
        records=_merge(page_events, page_messages),
        next_cursor=encode_cursor(start_seq) if _has_older(events, messages, start_seq) else None,
        last_seq=state.last_seq(conversation.id, state.UI_EVENT_CHANNEL),
    )


# 视图跑在事件循环上，而这里是一串同步 ORM 读，整个操作进工作线程，不逐句拆开。
aread_page = sync_to_async(read_page)


def _resolve_page_start(events: QuerySet[ConversationUiEvent], *, runs: int) -> int:
    """往更早的方向数 ``runs`` 个 run 边界，返回这一页该从哪个 seq 开始。

    只扫最多 :data:`MAX_PAGE_EVENTS` 行，所以这是一次**有界**的倒序索引扫描，而不是对整个会话做
    ``GROUP BY run_id``（那个的代价随会话长度增长，翻第一页和翻第一百页一样贵）。同一个 run 的
    事件 seq 连续，于是倒着看 ``run_id`` 一变就是一个 run 的开头，不聚合也能认出边界。

    撞上上限时**宁可少给几轮，也停在 run 边界上**：少给几轮客户端只是要多翻一页，切出半个 run 却
    会让那一页没法回放。只有连一轮都没数完（单个 run 的事件比上限还多）才不得不切在中间，那也没
    有别的选择了。分页本身不受影响：游标语义只关心「比这个位置更早的」，从不要求它是个 run 起点。

    :param events: 已经按 ``before_seq`` 收过口的事件集合。
    :param runs: 想要覆盖的轮数。
    :return: 本页最早一条事件的 seq；``0`` 表示这个范围里根本没有事件。
    """
    # 多读一行，只为了区分「这个范围就这么多事件」和「撞上了上限」——两种情况下走完循环该返回的
    # 东西不一样。这一行本身不进页。
    scanned = list(events.order_by("-seq").values_list("seq", "run_id")[: MAX_PAGE_EVENTS + 1])
    if not scanned:
        return 0
    capped = len(scanned) > MAX_PAGE_EVENTS
    page_rows = scanned[:MAX_PAGE_EVENTS]

    start_seq = page_rows[0][0]
    last_boundary: int | None = None
    closed_runs = 0
    # 成对地往更早的方向走。`older` 的 run 和 `newer` 的不一样，说明 `newer` 正是它那个 run 的第
    # 一个事件，也就是又数完了一轮。
    for (newer_seq, newer_run), (older_seq, older_run) in pairwise(page_rows):
        if older_run != newer_run:
            closed_runs += 1
            last_boundary = newer_seq
            if closed_runs == runs:
                return newer_seq
        start_seq = older_seq

    # 手里这批行走完了还没数够 `runs` 轮，两种原因要分开处理：
    #
    # * 这个范围本来就只有这么多事件——`start_seq` 就是会话的开头，正是要的；
    # * 撞上了上限——退回最后一个 run 边界，把凑不整的那半轮留给下一页。
    if capped and last_boundary is not None:
        return last_boundary
    return start_seq


def _has_older(
    events: QuerySet[ConversationUiEvent],
    messages: QuerySet[ConversationUserMessage],
    start_seq: int,
) -> bool:
    """这一页之前还有没有东西。

    分开问两张表，而不是简单判断 ``start_seq > 1``：后者依赖「事件 seq 从 1 起连续」这个由别处
    保证的性质，而「还有没有更早的」本来就可以直接问。

    :param events: 已经按 ``before_seq`` 收过口的事件集合。
    :param messages: 同一范围内的用户输入集合。
    :param start_seq: 本页的起始 seq。
    :return: 更早的位置上还有记录时为 ``True``。
    """
    if start_seq == 0:
        # 这个范围里没有事件，也就没有更早的位置可去了：见 `_resolve_page_start` 的返回约定。
        return False
    return events.filter(seq__lt=start_seq).exists() or messages.filter(after_seq__lt=start_seq - 1).exists()


def _merge(
    events: list[ConversationUiEvent],
    messages: list[ConversationUserMessage],
) -> list[ConversationHistoryRecord]:
    """把两条流合成一条，用户输入插在它创建时记录的 UI event 游标之后。

    两端时钟可能不同，事件回写也晚于输入落库，不能按时间戳混排。例如输入记录 after_seq=3，
    就始终插在 seq=3 后、seq=4 前，即使后续回写的事件来自上一轮 run，也不移动这个位置。
    UI event 的 seq 是 Runtime 跨重启延续的顺序，旧会话没有用户消息也仍然可以完整读取。

    :param events: 本页事件，按 seq 正序。
    :param messages: 本页用户输入，按 ``(after_seq, id)`` 正序。
    :return: 按对话顺序排列的历史实体，包含尚无事件的用户消息。
    """
    records: list[ConversationHistoryRecord] = []
    next_message = 0

    for event in events:
        while next_message < len(messages) and messages[next_message].after_seq < event.seq:
            records.append(_record_for_user_message(messages[next_message]))
            next_message += 1
        records.append(_record_for_ui_event(event))
    records.extend(_record_for_user_message(message) for message in messages[next_message:])
    return records


def _record_for_user_message(message: ConversationUserMessage) -> ConversationHistoryRecord:
    return ConversationHistoryRecord(user_message=UserMessageHistoryRecord.model_validate(message))


def _record_for_ui_event(event: ConversationUiEvent) -> ConversationHistoryRecord:
    return ConversationHistoryRecord(ui_event=UiEventRecord.model_validate(event.as_record()))
