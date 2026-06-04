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

"""系统态 API 视图，仅供平台内部系统（如 AIDev）通过 API 网关调用。"""

import logging

from rest_framework import viewsets
from rest_framework.response import Response

from paasng.infras.accounts.oauth.exceptions import BKAppOauthError
from paasng.infras.accounts.utils import create_app_oauth_backend
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class SysAIAgentAppUserTokenViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """以系统身份为 AI Agent 应用签发用户态 OAuth AccessToken，仅限 AIDev 系统角色调用。

    AIDev 平台在「在线调试智能体插件」场景中，需要获取目标应用的 AccessToken 以完成调试流程。
    但 AIDev 平台的智能体插件应用成员与开发者中心的应用成员没有同步机制，因此需要通过系统态接口签发用户态 Token。
    """

    permission_classes = [sysapi_client_perm_class(ClientAction.FETCH_AI_AGENT_APP_USER_TOKEN)]

    def fetch_user_token(self, request, app_code: str, env_name: str):
        """以系统身份获取指定 AI Agent 应用和用户的用户态 AccessToken"""
        # 该接口以系统 API 客户端角色（AIDev）鉴权，刻意绕过用户态的应用成员权限校验，
        # 因此使用 get_application_without_perm 获取应用，不能用带成员鉴权的 get_application。
        application = self.get_application_without_perm()
        # 仅允许为 AI Agent 应用签发 Token，避免系统态接口被用于签发任意应用的用户态 Token。
        if not application.is_ai_agent_app:
            raise error_codes.APP_IS_NOT_AI_AGENT

        try:
            backend = create_app_oauth_backend(application, env_name=env_name)
        except BkOauthClientDoesNotExist:
            raise error_codes.CLIENT_CREDENTIALS_MISSING

        try:
            data = backend.fetch_token(
                username=request.user.username, user_credential=backend.get_user_credential_from_request(request)
            )
        except BKAppOauthError as e:
            return Response(status=e.response_code, data={"message": e.error_message})

        sys_client = getattr(request, "sysapi_client", None)
        sys_client_name = sys_client.name if sys_client else "unknown"
        add_app_audit_record(
            app_code=app_code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ACCESS_TOKEN,
            attribute=f"sys_client:{sys_client_name}",
            data_after=DataDetail(data=data),
        )
        return Response(data=data)
