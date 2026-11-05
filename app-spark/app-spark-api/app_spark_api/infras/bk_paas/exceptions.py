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

"""调用开发者中心失败时抛出的异常。

这里只描述「开发者中心说了什么」，不决定给用户看什么文案；文案由调用方按场景决定。
"""

from typing import Any


class BkPaaSError(Exception):
    """Base class of every failure calling the BlueKing PaaS developer center."""


class BkPaaSConfigurationError(BkPaaSError):
    """This service is not configured to reach the developer center, which an operator has to fix."""


class BkPaaSUnavailableError(BkPaaSError):
    """The developer center answered something unreadable.

    超时、连不上这类网络错误不会转成它，按 httpx2.HTTPError 原样抛出，和 agent 侧的 bkaidev 客户端一致。
    """


class BkPaaSApiError(BkPaaSError):
    """The developer center answered with a non-2xx status.

    :param status_code: HTTP 状态码。
    :param code: 开发者中心的错误码，如 APP_SPARK_APP_REQUIRED；网关层拒绝时可能没有。
    :param message: 开发者中心给出的错误信息，可以直接展示给用户。
    :param fields_detail: 参数校验失败时每个字段的错误，其余情况为空。
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        code: str | None = None,
        fields_detail: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields_detail = fields_detail or {}
        super().__init__(f"BlueKing PaaS API {status_code} ({code or 'no code'}): {message}")
