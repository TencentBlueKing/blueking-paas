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

from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from paasng.infras.accounts.oauth.backends import get_bkapp_oauth_backend_cls
from paasng.infras.accounts.oauth.exceptions import BKAppOauthError
from paasng.infras.accounts.utils import create_app_oauth_backend
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.misc.audit.constants import AccessType, OperationEnum, OperationTarget
from paasng.misc.audit.service import add_app_audit_record
from paasng.platform.applications.mixins import SysManagedAppInPathMixin
from paasng.utils.error_codes import error_codes

from .api import make_access_token_detail


class SysOauthTokenViewSet(viewsets.ViewSet, SysManagedAppInPathMixin):
    permission_classes = [sysapi_client_perm_class(ClientAction.FETCH_APP_ACCESS_TOKEN)]

    @swagger_auto_schema(tags=["Oauth"], operation_id="sys_fetch_app_access_token")
    def fetch_app_token(self, request, code: str, env_name: str):
        """以用户凭证为 AI Agent 应用申请 AccessToken, 仅 AIDEV 可调用, 仅允许操作 AI Agent 应用

        信任边界: 本接口信任 AIDEV 是合法的托管方, 只校验调用方角色与目标应用归属, 不校验凭证对应的用户是否对该应用有权限.
        """
        application = self.get_managed_application_via_path()

        # 凭证头与平台使用的后端类型一一对应, 先校验凭证
        backend_cls = get_bkapp_oauth_backend_cls()
        user_credential = backend_cls.get_user_credential_from_headers(request)
        account = backend_cls.resolve_user_account(user_credential)
        username = account.bk_username

        # 跨租户借用用户身份属于越权, 不在 "AIDEV 托管" 的范围内.
        if settings.ENABLE_MULTI_TENANT_MODE and account.tenant_id != application.tenant_id:
            raise error_codes.USER_APP_TENANT_MISMATCH

        try:
            backend = create_app_oauth_backend(application, env_name=env_name)
        except BkOauthClientDoesNotExist:
            raise error_codes.CLIENT_CREDENTIALS_MISSING

        try:
            data = backend.fetch_token(username=username, user_credential=user_credential)
        except BKAppOauthError as e:
            # 请求上游失败时可能没有状态码, 兜底为 400, 避免 Response 拿到 None
            return Response(status=e.response_code or status.HTTP_400_BAD_REQUEST, data={"message": e.error_message})

        # 签发 token 成功后添加审计记录, operator 为凭证对应的用户
        add_app_audit_record(
            app_code=code,
            tenant_id=application.tenant_id,
            user=user_id_encoder.encode(settings.USER_TYPE, username),
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ACCESS_TOKEN,
            access_type=AccessType.API,
            data_after=make_access_token_detail(data, env_name),
        )
        return Response(data=data)
