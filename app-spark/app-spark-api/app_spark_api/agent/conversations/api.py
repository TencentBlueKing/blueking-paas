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

from app_spark_api.agent.conversations import services
from app_spark_api.agent.conversations.entities import (
    ErrorResponse,
    RuntimeStateResponse,
    StartRunRequest,
    UiEventPageResponse,
)
from app_spark_api.agent.conversations.models import Conversation
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
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
    """看一眼会话现在到哪儿了，不会为它拉起 Runtime。"""
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
    """把用户这一轮的话交给 Agent，并把 AG-UI 的 SSE 事件流原样透传回去。

    透传的是原始字节，而不是 ninja 的 ``SSE[Schema]``：本服务不需要认识 AG-UI 的事件结构，
    每个 token delta 都做一次 pydantic 校验加 JSON 重新序列化也纯属浪费。
    """
    conversation = await _get_conversation(request, project_id, number)

    # 所有 ORM 操作都必须在返回 StreamingHttpResponse 之前做完：生成器要跑到 run 结束为止，
    # 中途碰 ORM 会把一条数据库连接钉在一次可能长达数分钟的 run 上。
    run = await services.start_run(conversation, content=payload.content)

    return StreamingHttpResponse(
        services.stream_run(run, conversation.id),
        content_type="text/event-stream",
        headers=SSE_RESPONSE_HEADERS,
    )


@router.get(
    "{number}/ui-events/",
    response=UiEventPageResponse,
    url_name="conversations-ui-events",
    summary="补拉 AG-UI 事件历史",
)
async def list_ui_events(
    request: HttpRequest,
    number: int,
    project_id: str = PROJECT_ID,
    since: int = Query(0, ge=0, description="从这个游标之后开始读"),
    limit: int | None = Query(None, ge=1, description="每页条数，不传则用本服务的默认值"),
):
    """SSE 断了以后用来补上错过的事件——事件流本身没有重放能力。

    直接读本服务的库，不会为此拉起 Runtime。代价是最终一致：Runtime 是把事件流发完之后才回写
    的，所以刚结束的那一轮可能还差一点。要确认是否已经落定，看 `GET .../conversations/<n>/`
    的 `running` 与 `replication_pending` 是否都是 false。
    """
    conversation = await _get_conversation(request, project_id, number)
    page = await services.read_ui_events(conversation, since=since, limit=limit)
    return UiEventPageResponse(
        since=page.since,
        last_seq=page.last_seq,
        exhausted=page.exhausted,
        records=page.records,
    )


async def _get_project(request: HttpRequest, project_id: str) -> Project:
    """Return a Project the caller is allowed to reach, or raise 404.

    Scoped by tenant, which is the only boundary this project currently encodes. Nothing yet
    distinguishes members of one tenant from each other.

    TODO: narrow this to the Project's own members once there is a permission model to consult.
    """
    return await aget_object_or_404(
        Project.objects,
        id=project_id,
        tenant_id=get_tenant(authenticated_user(request)).id,
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
        model=state.model,
        context_version=state.context_version,
        log_seq=state.log_seq,
        ui_event_seq=state.ui_event_seq,
        running=state.running,
        replication_pending=state.replication_pending,
    )
