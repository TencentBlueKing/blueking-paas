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

"""首次发布前检查应用名称。

问不到开发者中心时要把原因告诉前端。发起发布时的检查在 services 里，问不到就放行，
创建应用还会再验一次。两套行为不收成一个函数。
"""

import re
from typing import TYPE_CHECKING

import attrs
import httpx2

from app_spark_api.infras.bk_paas import BkPaaSClient, BkPaaSError
from app_spark_api.publication import steps
from app_spark_api.publication.constants import APP_NAME_MAX_LENGTH

if TYPE_CHECKING:
    from app_spark_api.core.projects.models import Project

# 开发者中心的应用名称（NickNameField）去掉首尾空白后只保留这些字符，其余静默丢掉。
_APP_NAME_CHAR = re.compile(r"[\u4e00-\u9fa5\w\-_]")
MSG_APP_NAME_UNUSABLE = "应用名称只能包含中文、英文字母、数字、连接符和下划线"


@attrs.frozen
class AppNameValidationRet:
    """Whether the first deployment could create the application under a name.

    :param name: 按开发者中心的规则过滤、截断后实际会用的名称，什么也不剩时为空字符串。
    :param problem: 开发者中心的错误码，能用时为 None。unique 表示已被占用。
    :param message: 给用户看的说明，能用时为 None。
    """

    name: str
    problem: str | None
    message: str | None

    @property
    def is_available(self) -> bool:
        """Whether the name can be used."""
        return self.problem is None


def normalize_app_name(name: str) -> str:
    """Return the name the developer center would keep, cut to its length limit."""
    return "".join(_APP_NAME_CHAR.findall(name.strip()))[:APP_NAME_MAX_LENGTH]


def resolve_default_app_name(project: Project) -> str:
    """Return the application name to suggest on the first deployment."""
    # 项目名称一般比 ID 好读；全是开发者中心不认的字符时退回 ID。
    return normalize_app_name(project.name) or project.id


async def validate_app_name(project: Project, name: str) -> AppNameValidationRet:
    """Tell whether the first deployment could create the Project's application under this name.

    已绑定应用的项目发布时不再用到名称，前端不必为它调用。

    :raises PublicationStepError: 开发者中心没能给出结论，message 是给用户看的原因。
    """
    normalized = normalize_app_name(name)

    # 过滤后什么也不剩，不必问开发者中心，所以没有它的错误码。invalid 表示格式过不去。
    if not normalized:
        return AppNameValidationRet(name="", problem="invalid", message=MSG_APP_NAME_UNUSABLE)

    try:
        async with BkPaaSClient.from_settings() as client:
            result = await client.validate_app_basic_info(normalized, **steps.build_app_tenant_kwargs(project))
    except (BkPaaSError, httpx2.HTTPError) as exc:
        raise steps.to_step_error(exc) from exc

    error = result.name_error
    if error is None:
        return AppNameValidationRet(name=normalized, problem=None, message=None)

    return AppNameValidationRet(name=normalized, problem=error.problem, message=error.message)
