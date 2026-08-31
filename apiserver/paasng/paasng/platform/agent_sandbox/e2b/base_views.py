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

from rest_framework import viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import set_rollback

from .authentication import E2BApiKeyAuthentication


def e2b_exception_handler(exc, context):
    """把异常渲染成 e2b 的错误体：``{"code": <状态码>, "message": "<描述>"}``。

    SDK 只认 ``message`` 这个键（``e2b.api.handle_api_exception``），
    平台默认的 ``{"code", "detail", "login_url"}`` 它取不到描述，
    未认证时还会把 bkpaas 的登录地址泄露给 e2b 客户端。
    """
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
