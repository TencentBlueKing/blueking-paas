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

"""各步骤失败时给用户看的原因，以及失败属于哪一类。"""

from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING

from app_spark_api.infras.bk_paas import BkPaaSApiError, BkPaaSConfigurationError, BkPaaSError
from app_spark_api.publication.constants import DEPLOY_TIMEOUT
from app_spark_api.publication.packaging import SourcePackagingError

if TYPE_CHECKING:
    import httpx2

# 给用户看的失败原因。开发者中心返回的业务错误原样展示，下面这些是它没给出可读信息时的说法。
MSG_BKPAAS_UNAVAILABLE = "开发者中心暂时不可用"
MSG_APP_NOT_MANAGED = "该应用已在开发者中心改为其他部署方式，AppSpark 无法继续管理，请到开发者中心操作"
MSG_NOT_AUTHORIZED = "AppSpark 未获得开发者中心授权，请联系管理员"
MSG_NOT_CONFIGURED = "AppSpark 未完成开发者中心对接配置，请联系管理员"
MSG_DEPLOY_FAILED = "部署失败，请到开发者中心查看部署日志"
MSG_DEPLOY_INTERRUPTED = "部署已在开发者中心被中断"
MSG_POLL_FAILED = "多次查询部署结果都没有成功，请到开发者中心查看部署进度"
MSG_PREPARE_INTERRUPTED = "发布因服务重启中断，请重试"
MSG_PREPARE_FAILED = "发布时出现内部错误，请重试"
MSG_DEPLOY_UNCERTAIN = "部署请求可能已经提交，请到开发者中心查看部署记录"
MSG_MODULE_NOT_DEFAULT = "AppSpark 只能发布应用的默认模块，该应用的默认模块已在开发者中心变更，请到开发者中心操作"
MSG_APP_NOT_RECORDED = "开发者中心已创建应用 {code}，但 AppSpark 没能记下它，请联系管理员"
MSG_PROJECT_DELETED = "项目已删除，发布随之终止"
MSG_APP_NAME_TAKEN = "应用名称「{name}」已被开发者中心的其他应用使用，请换一个名称"
_MSG_DEPLOY_TIMEOUT = "部署超过 {minutes} 分钟仍未结束，请到开发者中心查看部署进度"
# 开发者中心 403 的错误码与给用户的说法。不在这里的 403（调用方没注册为 AppSpark 角色、网关没授权）要管理员处理。
_FORBIDDEN_MESSAGES = {
    "APP_SPARK_APP_REQUIRED": MSG_APP_NOT_MANAGED,
    "APP_SPARK_MODULE_REQUIRED": MSG_MODULE_NOT_DEFAULT,
}


class FailureCause(StrEnum):
    """Who has to act on a failure; the API answers with a different status for each."""

    # 开发者中心按业务规则拒绝了（如应用 ID 已存在），用户看了原因自己能处理。
    REJECTED = "rejected"
    # 开发者中心连不上、返回 5xx 或限流，稍后重试。
    UNAVAILABLE = "unavailable"
    # 本服务没配好对接或没获得授权，要管理员处理。
    MISCONFIGURED = "misconfigured"
    # 本服务自己出错。
    INTERNAL = "internal"


class PublicationStepError(Exception):
    """某一步失败，message 就是给用户看的原因。"""

    def __init__(self, message: str, cause: FailureCause) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


class AppNameTakenError(PublicationStepError):
    """Creating the application was refused because another one took the name."""

    def __init__(self, name: str) -> None:
        super().__init__(MSG_APP_NAME_TAKEN.format(name=name), FailureCause.REJECTED)
        self.name = name


def to_step_error(exc: BkPaaSError | httpx2.HTTPError | SourcePackagingError) -> PublicationStepError:
    """把失败整理成给用户看的原因；网络错误说成开发者中心暂时不可用。"""
    if isinstance(exc, SourcePackagingError):
        return PublicationStepError(str(exc), FailureCause.REJECTED)

    if isinstance(exc, BkPaaSConfigurationError):
        return PublicationStepError(MSG_NOT_CONFIGURED, FailureCause.MISCONFIGURED)

    if isinstance(exc, BkPaaSApiError):
        if exc.status_code == HTTPStatus.FORBIDDEN:
            return _describe_forbidden(exc)

        # 限流的说明照样展示，但归为暂时不可用：过一会儿重试就好，不是用户做错了什么。
        if exc.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            return PublicationStepError(exc.message, FailureCause.UNAVAILABLE)

        # 5xx 的说明多半是英文的服务端报错，对用户没用，统一说暂时不可用。
        if exc.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
            return PublicationStepError(exc.message, FailureCause.REJECTED)

    return PublicationStepError(MSG_BKPAAS_UNAVAILABLE, FailureCause.UNAVAILABLE)


def _describe_forbidden(exc: BkPaaSApiError) -> PublicationStepError:
    # 几种 403 要分开说，只能靠错误码区分：有的要用户去开发者中心处理，有的要管理员处理。
    message = _FORBIDDEN_MESSAGES.get(exc.code or "")
    if message is not None:
        return PublicationStepError(message, FailureCause.REJECTED)

    return PublicationStepError(MSG_NOT_AUTHORIZED, FailureCause.MISCONFIGURED)


def make_deploy_timeout_message() -> str:
    """Return the reason recorded when a deployment outlives DEPLOY_TIMEOUT."""
    return _MSG_DEPLOY_TIMEOUT.format(minutes=int(DEPLOY_TIMEOUT.total_seconds() // 60))
