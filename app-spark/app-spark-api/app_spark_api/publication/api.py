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

"""项目发布到开发者中心的接口：查询状态、发起发布、确认结果。"""

# django-ninja 在运行时读取视图签名，HttpRequest 只在类型检查时导入，必须让注解保持为字符串。
from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.shortcuts import aget_object_or_404
from ninja import Path, Router, Status

from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.entities import ERROR_RESPONSES
from app_spark_api.error_codes import error_codes
from app_spark_api.infras.accounts.auth import authenticated_user, login_required
from app_spark_api.publication import services
from app_spark_api.publication.entities import DeploymentCreateRequest, PublicationResponse
from app_spark_api.publication.exceptions import (
    PublicationAppNameInvalidError,
    PublicationNoVersionError,
    PublicationSubmitError,
    PublicationTaskInProgressError,
    PublicationVersionNotFoundError,
)

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router(tags=["publication"], auth=login_required)

PROJECT_ID = Path(..., description="项目 ID")


@router.get(
    "",
    response={**ERROR_RESPONSES, HTTPStatus.OK: PublicationResponse},
    url_name="publication-retrieve",
    summary="查看 Project 在开发者中心的发布状态",
)
async def get_publication(request: HttpRequest, project_id: str = PROJECT_ID):
    """线上版本、进行中的任务、最近一次失败、还没看过的结果和开发者中心页面链接。"""
    user = authenticated_user(request)
    project = await aget_object_or_404(Project.objects.owned_by(user.pk, tenant_id=get_tenant(user).id), id=project_id)
    return PublicationResponse.from_state(await services.get_publication_state(project))


@router.post(
    "deployments/",
    response={**ERROR_RESPONSES, HTTPStatus.ACCEPTED: PublicationResponse},
    url_name="publication-deployments-create",
    summary="把一个版本发布到开发者中心",
)
async def create_deployment(request: HttpRequest, payload: DeploymentCreateRequest, project_id: str = PROJECT_ID):
    """首次发布时同步创建应用，打包、部署在后台进行；已发布时为更新版本，线上旧版本在完成前继续服务。"""
    user = authenticated_user(request)
    project = await aget_object_or_404(Project.objects.owned_by(user.pk, tenant_id=get_tenant(user).id), id=project_id)

    # 发起人会成为开发者中心应用的管理员和各操作的记录人，开发者中心只认用户名。
    operator = user.username
    if not operator:
        raise error_codes.AUTHENTICATION_REQUIRED

    try:
        await services.start_deployment(project, payload.version_id, operator=operator, app_name=payload.app_name)
    except PublicationNoVersionError as exc:
        raise error_codes.PUBLICATION_NO_VERSION from exc
    except PublicationVersionNotFoundError as exc:
        raise error_codes.PUBLICATION_VERSION_NOT_FOUND.f(version_id=payload.version_id) from exc
    except PublicationAppNameInvalidError as exc:
        raise error_codes.PUBLICATION_APP_NAME_INVALID from exc
    except PublicationSubmitError as exc:
        raise error_codes.PUBLICATION_SUBMIT_FAILED.f(reason=str(exc)) from exc
    except PublicationTaskInProgressError as exc:
        raise error_codes.PUBLICATION_TASK_IN_PROGRESS from exc

    return Status(HTTPStatus.ACCEPTED, PublicationResponse.from_state(await services.get_publication_state(project)))


@router.delete(
    "unseen-result/",
    response={**ERROR_RESPONSES, HTTPStatus.NO_CONTENT: None},
    url_name="publication-unseen-result-delete",
    summary="确认已看过最近一次任务结果",
)
async def delete_unseen_result(request: HttpRequest, project_id: str = PROJECT_ID):
    """清空还没看过的结果，结果页只展示一次。"""
    user = authenticated_user(request)
    project = await aget_object_or_404(Project.objects.owned_by(user.pk, tenant_id=get_tenant(user).id), id=project_id)
    await services.clear_unseen_result(project)
    return Status(HTTPStatus.NO_CONTENT, None)
