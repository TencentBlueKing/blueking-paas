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

from django.shortcuts import aget_object_or_404
from ninja import Path, Router, Status
from ninja.pagination import paginate

from app_spark_api.core.projects import services
from app_spark_api.core.projects.constants import PROJECT_ID_PATTERN
from app_spark_api.core.projects.entities import ProjectCreateRequest, ProjectResponse
from app_spark_api.core.projects.exceptions import (
    ProjectAlreadyDeletedError,
    ProjectDeletionError,
    ProjectIdTakenError,
    ProjectNameTakenError,
)
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.entities import ERROR_RESPONSES
from app_spark_api.error_codes import error_codes
from app_spark_api.infras.accounts.auth import authenticated_user, login_required

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
    except ProjectNameTakenError as exc:
        raise error_codes.PROJECT_NAME_TAKEN.f(name=payload.name) from exc
    return Status(HTTPStatus.CREATED, project)


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


@router.delete(
    "/{project_id}/",
    response={**ERROR_RESPONSES, HTTPStatus.NO_CONTENT: None},
    url_name="projects-delete",
    summary="删除一个 Project 及其资源",
)
async def delete_project(request: HttpRequest, project_id: str = PROJECT_ID):
    """Delete a Project visible to its owner, ending its live conversations and releasing its resources."""
    user = authenticated_user(request)
    project = await aget_object_or_404(
        Project.objects.owned_by(user.pk, tenant_id=get_tenant(user).id),
        id=project_id,
    )

    try:
        await services.delete_project(project)
    except ProjectAlreadyDeletedError as exc:
        # 并发删除已经完成后，该项目与请求开始前就已删除的项目保持相同的不可见响应。
        raise error_codes.RESOURCE_NOT_FOUND from exc
    except ProjectDeletionError as exc:
        raise error_codes.PROJECT_DELETE_FAILED.f(category=exc.category) from exc

    return Status(HTTPStatus.NO_CONTENT, None)
