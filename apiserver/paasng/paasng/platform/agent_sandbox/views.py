# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.agent_sandbox.exceptions import SandboxAlreadyExists, SandboxError
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.sandbox import (
    create_sandbox,
    delete_sandbox,
)
from paasng.platform.agent_sandbox.serializers import SandboxCreateInputSLZ, SandboxCreateOutputSLZ
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class AgentSandboxViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    """Agent Sandbox 相关接口"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(
        tags=["agent_sandbox"],
        request_body=SandboxCreateInputSLZ(),
        responses={status.HTTP_201_CREATED: SandboxCreateOutputSLZ()},
    )
    def create(self, request, code):
        """创建一个新的 Agent Sandbox，新沙箱将自动进入运行状态。"""
        application = self.get_application()
        slz = SandboxCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            sandbox = create_sandbox(
                application=application,
                creator=request.user.pk,
                name=data.get("name"),
                env=data.get("env"),
            )
        except SandboxAlreadyExists:
            raise error_codes.AGENT_SANDBOX_ALREADY_EXISTS
        except SandboxError:
            logger.exception("Failed to create agent sandbox")
            raise error_codes.AGENT_SANDBOX_CREATE_FAILED
        return Response(SandboxCreateOutputSLZ(sandbox).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["agent_sandbox"], responses={status.HTTP_204_NO_CONTENT: ""})
    def destroy(self, request, code, sandbox_id):
        """停止并销毁一个 Agent Sandbox"""
        application = self.get_application()
        sandbox = Sandbox.objects.filter(application=application, uuid=sandbox_id, deleted_at__isnull=True).first()
        if not sandbox:
            raise error_codes.AGENT_SANDBOX_NOT_FOUND

        try:
            delete_sandbox(sandbox)
        except SandboxError:
            logger.exception("Failed to delete agent sandbox")
            raise error_codes.AGENT_SANDBOX_DELETE_FAILED
        return Response(status=status.HTTP_204_NO_CONTENT)
