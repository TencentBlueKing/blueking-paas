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

from ninja import Router, Status
from ninja.pagination import paginate

from app_spark_api.core.projects import services
from app_spark_api.core.projects.entities import ProjectCreateRequest, ProjectResponse
from app_spark_api.core.projects.exceptions import ProjectIdTakenError, ProjectNameTakenError
from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.entities import ErrorResponse
from app_spark_api.infras.accounts.auth import authenticated_user, login_required

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router(tags=["projects"], auth=login_required)


@router.post(
    "",
    response={HTTPStatus.CREATED: ProjectResponse, HTTPStatus.CONFLICT: ErrorResponse},
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
    except ProjectIdTakenError:
        return Status(HTTPStatus.CONFLICT, {"detail": f"Project id `{payload.id}` is already taken."})
    except ProjectNameTakenError:
        return Status(HTTPStatus.CONFLICT, {"detail": f"Project name `{payload.name}` is already taken."})
    return Status(HTTPStatus.CREATED, project)


@router.get(
    "",
    response=list[ProjectResponse],
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
