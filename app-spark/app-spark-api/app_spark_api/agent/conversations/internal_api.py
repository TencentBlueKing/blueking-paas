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

"""The endpoints an Agent Runtime writes its state back through.

Not part of the user-facing API and not authenticated as a user: the caller is a process this
service started itself, and it proves that with the token it was handed at spawn time. The
token names one conversation and every operation checks it against the one in the path, so a
Runtime cannot write into a conversation that is not its own even if it learns the address.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

# django-ninja resolves an operation's annotations at runtime to build its request parsers, so
# a type used in a path parameter cannot live in the TYPE_CHECKING block below.
from uuid import UUID  # noqa: TC003

from django.shortcuts import aget_object_or_404
from ninja import Field, Path, Router, Schema
from ninja.errors import HttpError

from app_spark_api.agent.conversations import checkpoints, state
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.agent.conversations.tokens import (
    InvalidStateToken,
    StateTokenClaims,
    read_state_token,
)
from app_spark_api.utils.urls import reverse_public

if TYPE_CHECKING:
    from django.http import HttpRequest

# Same reason `PROJECT_ID` exists in the user-facing router: django-ninja classifies a
# parameter it cannot find in the operation's own path as a query parameter.
CONVERSATION_ID = Path(..., description="会话 ID，必须与 token 指向的会话一致")

BEARER_PREFIX = "Bearer "

# The channel names the Runtime appends to the conversation-scoped root below. Named here
# because `state_ingest_path` derives that root by taking one of them back off again.
MESSAGES_SEGMENT = "messages"
UI_EVENTS_SEGMENT = "ui-events"
CONTEXT_SEGMENT = "context"
CHECKPOINT_SEGMENT = "checkpoint"

APPEND_MESSAGES_URL_NAME = "internal-append-messages"


async def runtime_token_required(request: HttpRequest) -> StateTokenClaims | None:
    """Authenticate a Runtime and hand the operation what its token claims.

    Returns the claims rather than resolving the row here, so the operation can compare them
    against its own path parameter. Reading the path from inside an auth callable would mean
    reaching into the URL resolver, which is both fragile and easy to get subtly wrong -- and
    getting it wrong here means one conversation writing into another.

    :param request: Request being authenticated.
    :return: The verified claims, or ``None`` to make django-ninja answer 401.
    """
    header = request.headers.get("Authorization", "")
    if not header.startswith(BEARER_PREFIX):
        return None
    try:
        return read_state_token(header.removeprefix(BEARER_PREFIX))
    except InvalidStateToken:
        return None


router = Router(tags=["internal"], auth=runtime_token_required)


def state_ingest_path(conversation_id: UUID) -> str:
    """Return the conversation-scoped root a Runtime writes its state under.

    Derived from a real route rather than assembled from a literal, so remounting this API
    somewhere else cannot quietly point a Runtime at nothing. The root itself has no route --
    it is a prefix, not an endpoint -- so the one route that does exist is reversed and its own
    last segment taken back off.

    The path is the public route, including FORCE_SCRIPT_NAME when the service is published
    under a sub-path. Whether that prefix should be kept is the provider's decision: a local
    process talks to uvicorn on loopback and must strip it; a remote sandbox that comes in
    through Ingress must keep it.

    :param conversation_id: Conversation the Runtime will be serving.
    :return: An absolute path, ending in a slash so the Runtime's own relative channel names
        resolve underneath it rather than replacing its last segment.
    """
    url = reverse_public(
        f"api:{APPEND_MESSAGES_URL_NAME}",
        kwargs={"conversation_id": conversation_id},
    )
    return url.removesuffix(MESSAGES_SEGMENT)


class ChannelRecord(Schema):
    """One append-only channel entry, exactly as the Runtime recorded it.

    The body is under whichever of ``message`` / ``event`` the channel uses, so both are
    optional here and the one that matters is picked per endpoint.
    """

    seq: int = Field(gt=0, description="会话内序号")
    run_id: str = Field(min_length=1, max_length=64, description="产生这条记录的 run")
    timestamp: str = Field(min_length=1, description="Runtime 侧记录时间，ISO-8601")
    message: Any = Field(default=None, description="原始模型消息，仅 messages 频道使用")
    event: Any = Field(default=None, description="AG-UI 事件，仅 ui-events 频道使用")


class AppendRequest(Schema):
    """One pushed batch. Entries must be in sequence order and contiguous."""

    records: list[ChannelRecord] = Field(description="要追加的记录")


class AppendResponse(Schema):
    """Where the channel stands now.

    Lower than the batch's own last entry when the batch was refused for leaving a gap, which
    is the Runtime's cue to rewind and re-send.
    """

    last_seq: int = Field(description="本频道当前已存到的最后一个游标")


class ContextResponse(Schema):
    """Which context version is now archived."""

    context_version: int = Field(description="已归档的上下文版本")


class CheckpointRequest(Schema):
    """一个已经到达远端的提交，以及它配套的会话位置。"""

    commit: str = Field(min_length=7, max_length=64, description="已推送的提交 SHA")
    tag: str = Field(min_length=1, max_length=255, description="钉住该提交的远端 tag")
    run_id: str = Field(min_length=1, max_length=64, description="产生这次提交的 run")
    context_version: int = Field(ge=0, description="和这次提交配套的上下文版本")


class CheckpointResponse(Schema):
    """这个检查点此刻能不能用来恢复。"""

    restorable: bool = Field(description="代码和配套上下文是否都已就位")


@router.post(
    f"{{conversation_id}}/state/{MESSAGES_SEGMENT}",
    response=AppendResponse,
    url_name=APPEND_MESSAGES_URL_NAME,
    summary="回写原始对话记录",
)
async def append_messages(
    request: HttpRequest,
    payload: AppendRequest,
    conversation_id: UUID = CONVERSATION_ID,
):
    return await _append(request, conversation_id, "message", payload)


@router.post(
    f"{{conversation_id}}/state/{UI_EVENTS_SEGMENT}",
    response=AppendResponse,
    url_name="internal-append-ui-events",
    summary="回写 AG-UI 事件历史",
)
async def append_ui_events(
    request: HttpRequest,
    payload: AppendRequest,
    conversation_id: UUID = CONVERSATION_ID,
):
    return await _append(request, conversation_id, "ui_event", payload)


@router.put(
    f"{{conversation_id}}/state/{CONTEXT_SEGMENT}",
    response=ContextResponse,
    url_name="internal-put-context",
    summary="回写会话上下文文档",
)
async def put_context(
    request: HttpRequest,
    conversation_id: UUID = CONVERSATION_ID,
):
    """把 Runtime 当前的可信上下文归档下来，也就是把冷启动唯一的依据存好。

    请求体是 Runtime 的 ``GET /context`` 原样吐出的那份文档，所以这里不用 ninja 的 Schema
    解析——本服务不需要认识上下文的内部结构，多做一次校验只会在 Runtime 的 schema 演进时变成
    一道必须同步修改的枷锁。
    """
    await _authorized_conversation(request, conversation_id)
    try:
        document = _json_object(await _read_json(request))
        version = await state.asave_context(conversation_id, document)
    except state.ConversationStateError as exc:
        raise HttpError(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc)) from exc
    return ContextResponse(context_version=version)


@router.put(
    f"{{conversation_id}}/state/{CHECKPOINT_SEGMENT}",
    response=CheckpointResponse,
    url_name="internal-put-checkpoint",
    summary="登记一个已推送到远端的可恢复点",
)
async def put_checkpoint(
    request: HttpRequest,
    payload: CheckpointRequest,
    conversation_id: UUID = CONVERSATION_ID,
):
    """记下 Runtime 刚推上去的那次提交，并回答它现在能不能用来恢复。

    游标不由 Runtime 报，而是在这里就地读当前已存到哪：Runtime 报的是它自己以为推到了哪，一旦
    某个批次其实没落库，恢复就会从一个并不存在的位置继续。这里读到的是真的存下来的。

    ``restorable`` 为 false 不是错误，是「代码到了、上下文还没到」这个正常的中间态。Runtime 之后
    重报同一个检查点即可，不需要——也不应该——再做一次提交。
    """
    conversation = await _authorized_conversation(request, conversation_id)
    restorable = await checkpoints.arecord(
        conversation_id,
        run_id=payload.run_id,
        commit=payload.commit,
        tag=payload.tag,
        context_version=payload.context_version,
        log_seq=await state.alast_seq(conversation_id, state.MESSAGE_CHANNEL),
        ui_event_seq=await state.alast_seq(conversation_id, state.UI_EVENT_CHANNEL),
        state_epoch=conversation.state_epoch,
    )
    return CheckpointResponse(restorable=restorable)


async def _append(
    request: HttpRequest,
    conversation_id: UUID,
    channel: str,
    payload: AppendRequest,
) -> AppendResponse:
    """Store one batch on behalf of the two append endpoints."""
    await _authorized_conversation(request, conversation_id)
    records = [record.dict() for record in payload.records]
    try:
        stored_through = await state.aappend_records(conversation_id, channel, records)
    except state.ConversationStateError as exc:
        raise HttpError(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc)) from exc
    return AppendResponse(last_seq=stored_through)


async def _authorized_conversation(request: HttpRequest, conversation_id: UUID) -> Conversation:
    """Return the conversation, having checked the token names exactly this one and is current.

    A mismatch is answered as 404 rather than 403: to a Runtime holding someone else's address,
    or one whose authority has been revoked, "this conversation does not exist for you" is the
    whole truth, and it leaks nothing.
    """
    # `request.auth` is what django-ninja stored from the auth callable; Django's own
    # `HttpRequest` knows nothing about it.
    claims: StateTokenClaims = request.auth  # type: ignore[attr-defined]
    if claims.conversation_id != str(conversation_id):
        raise HttpError(HTTPStatus.NOT_FOUND, "No such conversation.")
    conversation = await aget_object_or_404(Conversation.objects, id=conversation_id)
    if claims.epoch != conversation.state_epoch:
        # 这张 token 属于已经被吊销的那一代（比如上一代 Runtime 被显式终止过）。这个 Runtime
        # 可能还活着、还在推，但它写的已经不是当前这个会话该收的东西了。
        raise HttpError(HTTPStatus.NOT_FOUND, "No such conversation.")
    return conversation


async def _read_json(request: HttpRequest) -> Any:
    """Decode a request body this service forwards rather than validates."""
    try:
        return json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpError(HTTPStatus.UNPROCESSABLE_ENTITY, "Invalid JSON body.") from exc


def _json_object(payload: Any) -> dict[str, Any]:
    """Insist that a forwarded body is a JSON object."""
    if not isinstance(payload, dict):
        raise HttpError(HTTPStatus.UNPROCESSABLE_ENTITY, "Expected a JSON object.")
    return payload
