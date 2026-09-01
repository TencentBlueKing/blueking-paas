# -*- coding: utf-8 -*-
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

"""e2b 协议端点的公共基类。

e2b SDK 对响应体形态有硬性预期，与平台的蓝鲸 API 规范不一致，
所以协议端点要把渲染器与异常处理都换成 e2b 的形态。
"""

import logging

from rest_framework import status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import set_rollback

from .authentication import E2BApiKeyAuthentication
from .exceptions import (
    E2BClusterNotConfigured,
    E2BClusterUnavailable,
    E2BError,
    E2BGatewayError,
    E2BGatewayNotFound,
    E2BGatewayTimeout,
    E2BGatewayUnavailable,
    E2BSandboxNotFound,
)

logger = logging.getLogger(__name__)

# 兼容层异常到 e2b 响应的映射。
#
# 对外只给固定文案，不透出异常自带的信息：那里面有集群名、租户 ID、网关地址这类
# 内部拓扑，经错误响应外泄没有必要。原始信息进日志。
#
# 顺序有意义，按从具体到宽泛匹配，子类必须排在基类前面。
_ERROR_RESPONSES: tuple[tuple[type[E2BError], int, str], ...] = (
    (E2BSandboxNotFound, status.HTTP_404_NOT_FOUND, "Sandbox not found"),
    (E2BGatewayNotFound, status.HTTP_404_NOT_FOUND, "Sandbox not found"),
    (E2BGatewayTimeout, status.HTTP_408_REQUEST_TIMEOUT, "Sandbox service timed out, please retry"),
    (E2BGatewayUnavailable, status.HTTP_503_SERVICE_UNAVAILABLE, "Sandbox service is temporarily unavailable"),
    (E2BClusterUnavailable, status.HTTP_503_SERVICE_UNAVAILABLE, "Sandbox service is temporarily unavailable"),
    (E2BClusterNotConfigured, status.HTTP_503_SERVICE_UNAVAILABLE, "Sandbox service is temporarily unavailable"),
    # 网关返回了非 404 的错误码，成因不明，一律按上游故障处理
    (E2BGatewayError, status.HTTP_502_BAD_GATEWAY, "Sandbox service error"),
)


def _lookup_error_response(exc: E2BError) -> tuple[int, str] | None:
    for exc_type, status_code, message in _ERROR_RESPONSES:
        if isinstance(exc, exc_type):
            return status_code, message
    return None


def _e2b_error_response(exc: E2BError) -> Response:
    mapped = _lookup_error_response(exc)
    if mapped is None:
        logger.exception("unmapped e2b error, please add it to _ERROR_RESPONSES")
        mapped = (status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")

    status_code, message = mapped
    logger.warning("e2b request failed with %s: %s", type(exc).__name__, exc)
    set_rollback()
    return Response({"code": status_code, "message": message}, status=status_code)


def e2b_exception_handler(exc, context):
    """把异常渲染成 e2b 的错误体：``{"code": <状态码>, "message": "<描述>"}``。

    SDK 只认 ``message`` 这个键（``e2b.api.handle_api_exception``），
    平台默认的 ``{"code", "detail", "login_url"}`` 它取不到描述，
    未认证时还会把 bkpaas 的登录地址泄露给 e2b 客户端。
    """
    if isinstance(exc, E2BError):
        # 兼容层自己的异常。在这里统一转成响应，各端点就不必逐个 try/except，
        # 也就不会出现某个端点漏了映射、把内部异常直接冒成 500 的情况
        return _e2b_error_response(exc)

    if not isinstance(exc, APIException):
        # 非 DRF 异常交回上层，由 Django 的 500 处理链兜底
        return None

    detail = exc.detail
    if isinstance(detail, dict):
        message = "; ".join(f"{k}: {v}" for k, v in detail.items())
    elif isinstance(detail, list):
        message = "; ".join(str(item) for item in detail)
    else:
        message = str(detail)

    set_rollback()
    headers = {}
    if auth_header := getattr(exc, "auth_header", None):
        headers["WWW-Authenticate"] = auth_header
    return Response({"code": exc.status_code, "message": message}, status=exc.status_code, headers=headers)


class E2BProtocolViewSet(viewsets.GenericViewSet):
    """e2b 协议端点的基类。

    - 认证只认 ``X-API-Key``，与平台既有接口的 APIGW 认证完全隔离
    - 渲染器固定为原生 JSON，避免被蓝鲸规范的包装层改写响应体
    """

    authentication_classes = [E2BApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get_exception_handler(self):
        return e2b_exception_handler

    @property
    def api_key(self):
        """当前请求所用的 key 记录，由认证后端注入。"""
        return self.request.auth

    @property
    def application(self):
        """当前请求的归属应用。"""
        return self.request.auth.application
