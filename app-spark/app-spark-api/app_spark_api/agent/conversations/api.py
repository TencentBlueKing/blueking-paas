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

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.http import StreamingHttpResponse
from django.shortcuts import aget_object_or_404
from ninja import Path, Query, Router, Status
from ninja.pagination import paginate

from app_spark_api.agent.conversations import services
from app_spark_api.agent.conversations.entities import (
    ConversationResponse,
    RuntimeStateResponse,
    StartRunRequest,
    UiEventPageResponse,
)
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.entities import ErrorResponse
from app_spark_api.infras.accounts.auth import authenticated_user, login_required

if TYPE_CHECKING:
    from django.http import HttpRequest

    from app_spark_api.agent.conversations.services import ConversationState

router = Router(tags=["conversations"], auth=login_required)

# Nginx buffers a response body by default, which for an event stream means the client sees
# nothing until the run is over. django-ninja's own `SSE` format sets both of these; forwarding
# raw bytes means setting them here instead.
SSE_RESPONSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

# django-ninja reads path parameters out of each operation's own path, not out of the prefix the
# router was mounted under, so `project_id` has to say what it is. Left implicit it would be
# classified as a query parameter and every request would fail validation.
PROJECT_ID = Path(..., description="项目 ID")


@router.post(
    "",
    response={HTTPStatus.CREATED: RuntimeStateResponse, HTTPStatus.CONFLICT: ErrorResponse},
    url_name="conversations-create",
    summary="开始一个新会话",
)
async def create_conversation(request: HttpRequest, project_id: str = PROJECT_ID):
    """建一个会话，并把它的 Agent Runtime 拉起来。

    这里是唯一会顺手拉起 Runtime 的读接口：「新开一个会话」本身就意味着马上要干活，先把启动
    成本付掉，比让用户在第一句话上等着更好。
    """
    project = await _get_project(request, project_id)
    conversation = await services.create_conversation(project, owner=authenticated_user(request).pk)
    await services.open_client(conversation)
    return Status(HTTPStatus.CREATED, _to_state(conversation, await services.get_state(conversation)))


@router.get(
    "",
    response=list[ConversationResponse],
    url_name="conversations-list",
    summary="列出一个 Project 下的会话",
)
@paginate
async def list_conversations(
    request: HttpRequest,
    project_id: str = PROJECT_ID,
    is_live: bool | None = Query(None, description="只看还活着的（true）或已结束的（false）会话，不传则全都要"),
):
    """列出这个 Project 的会话，按创建时间倒序，可按是否还活着（live）过滤。

    「活着」指的是会话还没被结束、还能继续推进，而不是「此刻有没有 Agent Runtime 在跑」。
    Runtime 是可丢弃的，会被反复回收和重新拉起，那是会话的实现细节而不是会话的状态。
    """
    # 返回还没取值的 queryset：`@paginate` 会自己 COUNT 加切片，这里 `async for` 一遍再交出去
    # 等于把整个列表读进内存，翻页也就白翻了。
    return Conversation.objects.for_project(await _get_project(request, project_id), is_live=is_live)


@router.get(
    "{number}/",
    response=RuntimeStateResponse,
    url_name="conversations-retrieve",
    summary="查看会话状态",
)
async def get_conversation(
    request: HttpRequest,
    number: int,
    project_id: str = PROJECT_ID,
):
    """查看已创建的会话目前的状态，不会触发创建任何 Agent Runtime 逻辑。

    主要用于恢复一个历史会话，client 可根据返回里的状态信息拉取历史 AG-UI 事件。
    """
    conversation = await _get_conversation(request, project_id, number)
    return _to_state(conversation, await services.get_state(conversation))


@router.post(
    "{number}/runs/",
    response={HTTPStatus.OK: None, HTTPStatus.CONFLICT: ErrorResponse},
    url_name="conversations-start-run",
    summary="发起一轮对话，返回 AG-UI 事件流",
)
async def start_run(
    request: HttpRequest,
    number: int,
    payload: StartRunRequest,
    project_id: str = PROJECT_ID,
):
    """把用户本轮内容发送给 Agent，并把 AG-UI 的 SSE 事件流原样透传回去。

    - client 需要等待每轮会话结束后，再发送新的内容；
    - 已结束的会话不能再推进，会返回 409。

    AG-UI 协议说明：https://github.com/ag-ui-protocol/ag-ui
    """
    # 透传的是原始字节，而不是 ninja 的 ``SSE[Schema]``：本服务不需要认识 AG-UI 的事件结构，
    # 每个 token delta 都做一次 pydantic 校验加 JSON 重新序列化也纯属浪费。
    conversation = await _get_conversation(request, project_id, number)

    # 所有 ORM 操作都必须在返回 StreamingHttpResponse 之前做完：生成器要跑到 run 结束为止，
    # 中途碰 ORM 会把一条数据库连接钉在一次可能长达数分钟的 run 上。
    run = await services.start_run(conversation, content=payload.content)

    return StreamingHttpResponse(
        services.stream_run(run, conversation.id),
        content_type="text/event-stream",
        headers=SSE_RESPONSE_HEADERS,
    )


@router.post(
    "{number}/close/",
    response={HTTPStatus.OK: ConversationResponse, HTTPStatus.CONFLICT: ErrorResponse},
    url_name="conversations-close",
    summary="结束一个仍然活跃的会话",
)
async def close_conversation(
    request: HttpRequest,
    number: int,
    project_id: str = PROJECT_ID,
):
    """结束一个会话，并回收它占着的 Agent Runtime。

    - 结束是终态，重复调用会返回 409；
    - 会话的历史（AG-UI 事件等）不会被删掉，仍然可以读，只是不能再发起新的一轮对话；
    - 如果此刻正有一轮对话在跑，它会被打断，那条 SSE 流上会收到一个 AG-UI `RUN_ERROR` 事件。
    """
    conversation = await _get_conversation(request, project_id, number)
    # 已经结束的会话会抛 ConversationClosedError，由 `app_spark_api.api` 里的统一处理器翻成 409。
    await services.close_conversation(conversation)
    return conversation


@router.get(
    "{number}/ui-events/",
    response=UiEventPageResponse,
    url_name="conversations-ui-events",
    summary="拉取已入库的 AG-UI 事件历史",
)
async def list_ui_events(
    request: HttpRequest,
    number: int,
    project_id: str = PROJECT_ID,
    since: int = Query(0, ge=0, description="从这个游标之后开始读"),
    limit: int | None = Query(None, ge=1, description="每页条数，默认值 200"),
):
    """拉取已入库的 AG-UI 事件，用于恢复会话后展示历史对话内容，或在 SSE 以外终止后补上事件。"""
    # 直接读本服务的库，不会为此拉起 Runtime。代价是最终一致：Runtime 是把事件流发完之后才回写
    # 的，所以刚结束的那一轮可能还差一点。要确认是否已经落定，看 `GET .../conversations/<n>/`
    # 的 `running` 与 `replication_pending` 是否都是 false。
    conversation = await _get_conversation(request, project_id, number)
    page = await services.read_ui_events(conversation, since=since, limit=limit)
    return UiEventPageResponse(
        since=page.since,
        last_seq=page.last_seq,
        exhausted=page.exhausted,
        records=page.records,
    )


async def _get_project(request: HttpRequest, project_id: str) -> Project:
    """Return a Project the caller is allowed to reach, or raise 404."""
    user = authenticated_user(request)
    return await aget_object_or_404(
        Project.objects.owned_by(user.pk, tenant_id=get_tenant(user).id),
        id=project_id,
    )


async def _get_conversation(request: HttpRequest, project_id: str, number: int) -> Conversation:
    """Return one of the Project's conversations by its number, or raise 404.

    The Project is re-checked rather than trusted from the path, so a conversation cannot be
    reached by naming a Project the caller does happen to have. Numbers only being unique
    within a Project, that check is also what makes this lookup unambiguous.
    """
    project = await _get_project(request, project_id)
    return await aget_object_or_404(
        Conversation.objects,
        number=number,
        project=project,
    )


def _to_state(conversation: Conversation, state: ConversationState) -> RuntimeStateResponse:
    """Present a conversation's stored state as this API's own view of it."""
    return RuntimeStateResponse(
        number=conversation.number,
        conversation_id=conversation.id,
        is_live=conversation.is_live,
        closed_at=conversation.closed_at,
        model=state.model,
        context_version=state.context_version,
        log_seq=state.log_seq,
        ui_event_seq=state.ui_event_seq,
        running=state.running,
        replication_pending=state.replication_pending,
    )
