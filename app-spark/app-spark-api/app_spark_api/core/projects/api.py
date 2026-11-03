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

from ninja import Path, Router, Status
from ninja.pagination import paginate

from app_spark_api.core.projects import services, tasks
from app_spark_api.core.projects.constants import COLLECTION_ACTIONS_SEGMENT, PROJECT_ID_PATTERN
from app_spark_api.core.projects.entities import (
    ProjectCreateRequest,
    ProjectFromPromptRequest,
    ProjectFromPromptResponse,
    ProjectIntRenamingResponse,
    ProjectRenameRequest,
    ProjectResponse,
)
from app_spark_api.core.projects.exceptions import (
    ProjectAlreadyDeletedError,
    ProjectDeletionError,
    ProjectIdTakenError,
)
from app_spark_api.core.projects.models import Project, ProjIntRenaming
from app_spark_api.core.shortcuts import aget_project_or_404
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.entities import ERROR_RESPONSES
from app_spark_api.error_codes import error_codes
from app_spark_api.infras.accounts.auth import authenticated_user, login_required
from app_spark_api.infras.accounts.credentials import get_user_credential

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router(tags=["projects"], auth=login_required)
PROJECT_ID = Path(
    ...,
    pattern=PROJECT_ID_PATTERN,
    description="项目 ID，2-20 个字符，小写字母开头，仅含小写字母、数字与连字符",
)


@router.post(
    "",
    response={**ERROR_RESPONSES, HTTPStatus.CREATED: ProjectResponse},
    url_name="projects-create",
    summary="创建一个 Project",
)
async def create_project(request: HttpRequest, payload: ProjectCreateRequest):
    """创建一个 Project。"""
    user = authenticated_user(request)
    try:
        project = await services.create_project(
            project_id=payload.id,
            name=payload.name,
            owner=user.pk,
            tenant_id=get_tenant(user).id,
        )
    except ProjectIdTakenError as exc:
        raise error_codes.PROJECT_ID_TAKEN.f(project_id=payload.id) from exc
    return Status(HTTPStatus.CREATED, project)


@router.post(
    f"{COLLECTION_ACTIONS_SEGMENT}/create-from-prompt/",
    response={**ERROR_RESPONSES, HTTPStatus.CREATED: ProjectFromPromptResponse},
    url_name="projects-create-from-prompt",
    summary="用第一句话创建一个 Project",
)
async def create_project_from_prompt(request: HttpRequest, payload: ProjectFromPromptRequest):
    """用用户的第一句话创建一个 Project，并开好承接这句话的会话。

    - 项目 ID 由服务端生成，名称暂时与 ID 相同，之后会在后台自动改成更好认的名字；
    - 这句话不会由本接口发给 Agent。客户端拿到响应后，用返回的项目 ID 和会话编号调用
      `POST /projects/{project_id}/conversations/{number}/runs/` 把它作为第一轮对话发出，
      之后的交互与手动创建项目完全一致；
    - 本接口不拉起 Agent Runtime，准备运行环境的耗时落在第一轮对话上；
    - 自动命名在后台执行，客户端可轮询 `GET /projects/{project_id}/int-renaming/` 获取结果。
    """
    user = authenticated_user(request)
    created = await services.create_project_from_prompt(
        content=payload.content,
        owner=user.pk,
        tenant_id=get_tenant(user).id,
    )
    # 换 access_token 需要用户登录态，只有这里拿得到，所以要赶在响应之前把命名任务排好。
    await tasks.start_int_renaming(created.project, credential=get_user_credential(request))
    return Status(HTTPStatus.CREATED, {"project": created.project, "conversation": created.conversation})


@router.get(
    "/{project_id}/int-renaming/",
    response={**ERROR_RESPONSES, HTTPStatus.OK: ProjectIntRenamingResponse},
    url_name="projects-int-renaming",
    summary="查询项目的自动命名状态",
)
async def get_project_int_renaming(request: HttpRequest, project_id: str = PROJECT_ID):
    """查询一个项目的自动命名任务。

    只有用 `POST /projects/-/create-from-prompt/` 创建的项目有这个任务；手动创建的项目没有，
    返回 404。前端在创建后轮询本接口，直到 `status` 不再是 `pending`。
    """
    project = await aget_project_or_404(request, project_id)
    record = await ProjIntRenaming.objects.filter(project_id=project.pk).afirst()
    if record is None:
        raise error_codes.PROJECT_INT_RENAMING_NOT_FOUND
    return record


@router.get(
    "",
    response={**ERROR_RESPONSES, HTTPStatus.OK: list[ProjectResponse]},
    url_name="projects-list",
    summary="列出当前用户的 Project",
)
@paginate
async def list_projects(request: HttpRequest):
    """列出当前登录用户的 Project，按创建时间倒序。

    暂不支持自定义排序。目前也没有「别人的项目」这个说法可查：Project 上还没有成员或权限模型，
    所以列表固定按 owner 收在当前用户身上。
    """
    user = authenticated_user(request)
    # 返回还没取值的 queryset，翻页由 `@paginate` 完成，理由同会话列表。
    return Project.objects.owned_by(user.pk, tenant_id=get_tenant(user).id)


@router.post(
    "/{project_id}/rename/",
    response={**ERROR_RESPONSES, HTTPStatus.OK: ProjectResponse},
    url_name="projects-rename",
    summary="给一个 Project 改名",
)
async def rename_project(request: HttpRequest, payload: ProjectRenameRequest, project_id: str = PROJECT_ID):
    """给当前用户自己的 Project 改名；名称不要求唯一，可以和其他项目相同。"""
    project = await aget_project_or_404(request, project_id)

    try:
        project = await services.rename_project(project, name=payload.name)
    except ProjectAlreadyDeletedError as exc:
        # 取出之后被并发删除，与请求开始前就已删除的项目保持相同的不可见响应。
        raise error_codes.RESOURCE_NOT_FOUND from exc
    return project


@router.delete(
    "/{project_id}/",
    response={**ERROR_RESPONSES, HTTPStatus.NO_CONTENT: None},
    url_name="projects-delete",
    summary="删除一个 Project 及其资源",
)
async def delete_project(request: HttpRequest, project_id: str = PROJECT_ID):
    """Delete a Project visible to its owner, ending its live conversations and releasing its resources."""
    project = await aget_project_or_404(request, project_id)

    try:
        await services.delete_project(project)
    except ProjectAlreadyDeletedError as exc:
        # 并发删除已经完成后，该项目与请求开始前就已删除的项目保持相同的不可见响应。
        raise error_codes.RESOURCE_NOT_FOUND from exc
    except ProjectDeletionError as exc:
        raise error_codes.PROJECT_DELETE_FAILED.f(category=exc.category) from exc

    return Status(HTTPStatus.NO_CONTENT, None)
