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

from ninja import Path, Query, Router, Status

from app_spark_api.core.shortcuts import aget_project_or_404
from app_spark_api.entities import ERROR_RESPONSES
from app_spark_api.infras.accounts.auth import authenticated_user, login_required
from app_spark_api.publication import services
from app_spark_api.publication.entities import AppNameValidateResponse, DeploymentCreateRequest, PublicationResponse
from app_spark_api.publication.exceptions import (
    PublicationAppNameConflictError,
    PublicationAppNameInvalidError,
    PublicationNoVersionError,
    PublicationProjectGoneError,
    PublicationSubmitError,
    PublicationTaskInProgressError,
    PublicationVersionNotFoundError,
)
from app_spark_api.publication.steps import FailureCause, PublicationStepError
from app_spark_api.utils.api_errors.error_codes import error_codes

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router(tags=["publication"], auth=login_required)

PROJECT_ID = Path(..., description="项目 ID")

# 创建应用（或检查应用名称）失败时按该由谁处理给出不同的状态码，前端和监控据此区分用户能处理的拒绝与依赖故障。
_SUBMIT_ERRORS = {
    FailureCause.REJECTED: error_codes.PUBLICATION_SUBMIT_FAILED,
    FailureCause.UNAVAILABLE: error_codes.PUBLICATION_BKPAAS_UNAVAILABLE,
    FailureCause.MISCONFIGURED: error_codes.PUBLICATION_BKPAAS_MISCONFIGURED,
    FailureCause.INTERNAL: error_codes.PUBLICATION_INTERNAL_ERROR,
}


@router.get(
    "",
    response={**ERROR_RESPONSES, HTTPStatus.OK: PublicationResponse},
    url_name="publication-retrieve",
    summary="查看 Project 在开发者中心的发布状态",
)
async def get_publication(request: HttpRequest, project_id: str = PROJECT_ID):
    """线上版本、进行中的任务、最近一次失败、要不要展开最近一次结果和开发者中心页面链接。"""
    project = await aget_project_or_404(request, project_id)
    return PublicationResponse.from_state(await services.get_publication_state(project))


@router.post(
    "deployments/",
    response={**ERROR_RESPONSES, HTTPStatus.ACCEPTED: PublicationResponse},
    url_name="publication-deployments-create",
    summary="把一个版本发布到开发者中心",
)
async def create_deployment(request: HttpRequest, payload: DeploymentCreateRequest, project_id: str = PROJECT_ID):
    """首次发布时同步创建应用，打包、部署在后台进行；已发布时为更新版本，线上旧版本在完成前继续服务。"""
    project = await aget_project_or_404(request, project_id)

    # 发起人会成为开发者中心应用的管理员和各操作的记录人，开发者中心只认用户名。
    operator = authenticated_user(request).username
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
    except PublicationAppNameConflictError as exc:
        raise error_codes.PUBLICATION_APP_NAME_CONFLICT.f(name=exc.name) from exc
    except PublicationSubmitError as exc:
        raise _SUBMIT_ERRORS[exc.cause].f(reason=exc.message) from exc
    except PublicationTaskInProgressError as exc:
        raise error_codes.PUBLICATION_TASK_IN_PROGRESS from exc
    except PublicationProjectGoneError as exc:
        # 和取项目时一样按「不可见」处理，不暴露项目刚被删除。
        raise error_codes.RESOURCE_NOT_FOUND from exc

    return Status(HTTPStatus.ACCEPTED, PublicationResponse.from_state(await services.get_publication_state(project)))


@router.get(
    "app-name-validate/",
    response={**ERROR_RESPONSES, HTTPStatus.OK: AppNameValidateResponse},
    url_name="publication-app-name-validate",
    summary="检查首次发布时能否用某个名称创建开发者中心应用",
)
async def validate_app_name(
    request: HttpRequest,
    project_id: str = PROJECT_ID,
    name: str = Query(..., min_length=1, max_length=64, description="想用的应用名称，会按开发者中心的规则过滤"),
):
    """名称在开发者中心租户内唯一，发布面板在打开时和改名时调用，重名时提示用户换一个。

    返回过滤后实际会用的名称。已创建应用的项目发布时不再用到名称，不必调用。名称能否使用以发布时的校验为准，
    这里能用的名称在发布前仍可能被别人抢先使用。
    """
    project = await aget_project_or_404(request, project_id)

    try:
        validation = await services.validate_app_name(project, name)
    except PublicationStepError as exc:
        raise _SUBMIT_ERRORS[exc.cause].f(reason=exc.message) from exc

    return AppNameValidateResponse.from_validation(validation)


@router.delete(
    "unseen-result/",
    response={**ERROR_RESPONSES, HTTPStatus.NO_CONTENT: None},
    url_name="publication-unseen-result-delete",
    summary="确认已点开看过最近一次任务结果",
)
async def delete_unseen_result(request: HttpRequest, project_id: str = PROJECT_ID):
    """用户点开过最近一次任务的结果后调用，之后打开发布面板不再主动展开它。

    发布面板打开时，若 unseen_result 不为空，前端主动展开最近一次部署记录（成功或失败）；用户点开看过后调用
    本接口，unseen_result 随即为空，刷新页面也不会再弹出。线上版本、最近一次失败（last_failure）照常返回，
    不受本接口影响。下一次任务结束后 unseen_result 又会出现。
    """
    project = await aget_project_or_404(request, project_id)
    await services.clear_unseen_result(project)
    return Status(HTTPStatus.NO_CONTENT, None)
