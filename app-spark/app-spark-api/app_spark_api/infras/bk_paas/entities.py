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

"""开发者中心系统 API 的响应结构。

只收调用方用得到的字段。开发者中心的响应会带很多别的字段，所以这里用一个不拒绝多余键的
转换器，而不是项目通用的 cattrs_converter（那个是给配置用的，多一个键就报错）。
"""

from enum import StrEnum
from typing import Any

import attrs
from cattrs import Converter
from cattrs.errors import BaseValidationError

from app_spark_api.infras.bk_paas.exceptions import BkPaaSUnavailableError

_converter = Converter()


class DeploymentStatus(StrEnum):
    """Status of one deployment, as sys_get_deployment_result reports it."""

    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


# 只有这几个算结束。开发者中心以后新增的状态值按进行中处理，免得被当成读不懂的响应。
_FINISHED_STATUSES = frozenset({DeploymentStatus.SUCCESSFUL, DeploymentStatus.FAILED, DeploymentStatus.INTERRUPTED})


@attrs.frozen
class CreatedApp:
    """An application just created in the developer center.

    :param code: 应用 ID。
    :param name: 应用名称。
    :param default_module: 默认模块名，后续上传、部署都要用。
    """

    code: str
    name: str
    default_module: str

    @classmethod
    def from_payload(cls, payload: Any) -> CreatedApp:
        """Read the application out of a create_sys_app_spark_app response."""
        try:
            app = payload["application"]
            default_module = next(m["name"] for m in app["modules"] if m.get("is_default"))
            return cls(code=str(app["code"]), name=str(app["name"]), default_module=str(default_module))
        except (KeyError, TypeError, AttributeError, StopIteration) as exc:
            raise BkPaaSUnavailableError(f"Unreadable create-app response: {exc!r}") from exc


@attrs.frozen
class Deployment:
    """A deployment the developer center has accepted."""

    deployment_id: str


@attrs.frozen
class DeploymentResult:
    """Where one deployment has got to.

    :param status: 部署状态，常见取值见 DeploymentStatus，也可能是开发者中心新增的其他值。
    :param error_detail: 失败原因，成功或进行中时为空。
    :param access_url: 部署成功时为该环境的默认访问地址，其余情况为空。
    """

    status: str
    error_detail: str | None = None
    access_url: str | None = None

    @property
    def is_finished(self) -> bool:
        """Whether the deployment has stopped, one way or another."""
        return self.status in _FINISHED_STATUSES


def structure_payload[T](payload: Any, cls: type[T]) -> T:
    """Structure a developer center response into one of the classes above.

    :raises BkPaaSUnavailableError: 响应缺字段或类型不对，按开发者中心不可用处理。
    """
    try:
        return _converter.structure(payload, cls)
    except (BaseValidationError, KeyError, TypeError, ValueError, AttributeError) as exc:
        raise BkPaaSUnavailableError(f"Unreadable {cls.__name__} response: {exc!r}") from exc
