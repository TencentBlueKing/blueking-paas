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

"""e2b 的管理接口。

- ``E2BApiKeyViewSet``：给平台调用方用的，走平台既有的 APIGW 认证
- ``E2BConsole*ViewSet``：给开发者中心页面用的，走登录态与应用权限

用 key 本身去访问的 e2b 协议端点见 ``base_views.E2BProtocolViewSet``。
协议端点的路径由 SDK 规定、不含应用 code，登录态无法据此定位应用，所以页面不能直接复用协议端点。
"""

import logging

from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.agent_sandbox.models import E2BApiKey
from paasng.platform.agent_sandbox.permissions import IsAPIGWVerifiedApp
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

from . import sandboxes
from .exceptions import E2BApiKeyGenerateError, E2BApiKeyQuotaExceeded, E2BError, E2BSandboxNotFound
from .serializers import (
    E2BApiKeyCreateInputSLZ,
    E2BApiKeyCreateOutputSLZ,
    E2BApiKeyOutputSLZ,
    E2BConsoleApiKeyOutputSLZ,
    E2BConsoleSandboxListInputSLZ,
    E2BConsoleSandboxOutputSLZ,
)

logger = logging.getLogger(__name__)


class E2BApiKeyViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    """e2b API Key 的签发、列举与吊销。"""

    permission_classes = [IsAuthenticated, IsAPIGWVerifiedApp]

    @swagger_auto_schema(
        tags=["agent_sandbox.e2b"],
        request_body=E2BApiKeyCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: E2BApiKeyCreateOutputSLZ()},
    )
    def create(self, request, code):
        """签发一枚 e2b API Key，明文仅在本次响应中返回。"""
        application = self.get_application()
        slz = E2BApiKeyCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        try:
            key_obj, plain_key = E2BApiKey.objects.issue(
                application=application,
                owner=request.user.pk,
                name=slz.validated_data["name"],
            )
        except E2BApiKeyQuotaExceeded:
            raise error_codes.AGENT_SANDBOX_E2B_API_KEY_QUOTA_EXCEEDED
        except E2BApiKeyGenerateError:
            logger.exception("Failed to generate e2b api key for app %s", application.code)
            raise error_codes.AGENT_SANDBOX_E2B_API_KEY_CREATE_FAILED

        # 明文不入库，挂在实例上仅供本次响应序列化
        key_obj.api_key = plain_key
        return Response(E2BApiKeyCreateOutputSLZ(key_obj).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["agent_sandbox.e2b"],
        responses={status.HTTP_200_OK: E2BApiKeyOutputSLZ(many=True)},
    )
    def list(self, request, code):
        """列举本应用当前生效的 key，只返回前缀与元信息。

        已吊销的不返回：签发配额只统计生效中的 key，列表跟着同一口径才能用来判断还能签几枚；
        吊销记录只增不减，也不该让它撑大一个没有分页的响应。审计线索留在库里。
        """
        application = self.get_application()
        keys = E2BApiKey.objects.filter(application=application, enabled=True)
        return Response(E2BApiKeyOutputSLZ(keys, many=True).data)

    @swagger_auto_schema(tags=["agent_sandbox.e2b"], responses={status.HTTP_204_NO_CONTENT: ""})
    def destroy(self, request, code, key_id):
        """吊销一枚 key。置为失效而非物理删除，保留审计线索。"""
        application = self.get_application()
        # 不属于本应用的 key 一律按不存在处理，不区分「无权限」与「不存在」
        key_obj = get_object_or_404(E2BApiKey, uuid=key_id, application=application)
        key_obj.revoke()
        return Response(status=status.HTTP_204_NO_CONTENT)


class E2BConsoleApiKeyViewSet(E2BApiKeyViewSet):
    """开发者中心页面管理 e2b API Key，签发与吊销的行为与 APIGW 版本一致。"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(
        tags=["agent_sandbox.e2b"],
        responses={status.HTTP_200_OK: E2BConsoleApiKeyOutputSLZ(many=True)},
    )
    def list(self, request, code):
        """列举本应用当前生效的 key，额外返回签发人供页面展示。"""
        application = self.get_application()
        keys = E2BApiKey.objects.filter(application=application, enabled=True)
        return Response(E2BConsoleApiKeyOutputSLZ(keys, many=True).data)


class E2BConsoleSandboxViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    """开发者中心页面查看与销毁本应用的 e2b 沙箱。"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(
        tags=["agent_sandbox.e2b"],
        query_serializer=E2BConsoleSandboxListInputSLZ(),
        responses={status.HTTP_200_OK: E2BConsoleSandboxOutputSLZ(many=True)},
    )
    def list(self, request, code):
        """列出本应用名下存活的沙箱，某个集群不可达时跳过该集群。"""
        application = self.get_application()
        slz = E2BConsoleSandboxListInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        items = sandboxes.list_sandboxes(application)
        if template_id := slz.validated_data.get("template_id"):
            items = [item for item in items if item.get("templateID") == template_id]
        return Response(E2BConsoleSandboxOutputSLZ(items, many=True).data)

    @swagger_auto_schema(tags=["agent_sandbox.e2b"], responses={status.HTTP_204_NO_CONTENT: ""})
    def destroy(self, request, code, sandbox_id):
        """销毁沙箱，重复调用幂等。"""
        application = self.get_application()
        try:
            sandboxes.kill_sandbox(application, sandbox_id)
        except E2BSandboxNotFound:
            raise error_codes.AGENT_SANDBOX_E2B_SANDBOX_NOT_FOUND
        except E2BError as exc:
            # 异常信息里有集群名、网关地址，只进日志，不进响应
            logger.warning("failed to kill e2b sandbox %s for app %s: %s", sandbox_id, application.code, exc)
            raise error_codes.AGENT_SANDBOX_E2B_SERVICE_UNAVAILABLE
        return Response(status=status.HTTP_204_NO_CONTENT)
