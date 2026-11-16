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


# 开发者中心表示「已被占用」的字段错误码。只有这个要单独处理（让用户换名），其余 code 原样传出。
UNIQUE_APP_FIELD_CODE = "unique"


@attrs.frozen
class AppFieldError:
    """One field the developer center would refuse.

    :param problem: 开发者中心的错误码，如 unique、max_length。没有 code 时记为 invalid。
    :param message: 开发者中心给出的说明，可以直接展示给用户。
    """

    problem: str
    message: str


@attrs.frozen
class AppBasicInfoValidation:
    """Whether the developer center would accept an application ID and name, as sys_validate_app_basic_info says.

    :param code_error: 应用 ID 不能用的原因，能用或没校验时为 None。
    :param name_error: 应用名称不能用的原因，能用时为 None。
    """

    code_error: AppFieldError | None
    name_error: AppFieldError | None

    @classmethod
    def from_payload(cls, payload: Any) -> AppBasicInfoValidation:
        """Read the result out of a sys_validate_app_basic_info response."""
        try:
            fields_detail = payload["fields_detail"]
            return cls(
                code_error=_read_field_error(fields_detail.get("code")),
                name_error=_read_field_error(fields_detail.get("name")),
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise BkPaaSUnavailableError(f"Unreadable app validation response: {exc!r}") from exc


def _read_field_error(errors: Any) -> AppFieldError | None:
    if not errors:
        return None

    # 同一字段可能有多条。有占用就报 unique，换名字时格式问题一并解决；否则原样传第一条的 code。
    chosen = errors[0]
    for error in errors:
        if error.get("code") == UNIQUE_APP_FIELD_CODE:
            chosen = error
            break

    return AppFieldError(problem=str(chosen.get("code") or "invalid"), message=str(chosen["message"]))


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
