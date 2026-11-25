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

from typing import TYPE_CHECKING
from unittest import mock

import pytest
from bkpaas_auth.core.token import UserAccount
from django.test.utils import override_settings
from rest_framework import status

from paasng.infras.accounts.oauth.backends import get_bkapp_oauth_backend_cls
from paasng.misc.audit.constants import OperationTarget
from paasng.misc.audit.models import AppOperationRecord

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

APP_TENANT_ID = "tenant-app"
ACCESS_TOKEN = "real-access-token"
REFRESH_TOKEN = "real-refresh-token"
EXPIRES_IN = 3600
FAKE_TOKEN_DATA = {"access_token": ACCESS_TOKEN, "refresh_token": REFRESH_TOKEN, "expires_in": EXPIRES_IN}


def _token_url(app_code: str) -> str:
    return f"/sys/api/bkapps/applications/{app_code}/oauth/token/prod/"


@pytest.fixture()
def stubbed_oauth_backend():
    """拦截用应用身份换 token 的远程调用, 返回固定的签发结果。"""
    backend_cls = get_bkapp_oauth_backend_cls()
    backend = backend_cls(
        auth_url="http://token.example.com",
        refresh_url="http://token.example.com/refresh",
        validate_url=None,
        app_code="fake-app-code",
        app_secret="fake-app-secret",
        env_name="prod",
    )
    backend.fetch_token = mock.Mock(return_value=dict(FAKE_TOKEN_DATA))
    with mock.patch("paasng.infras.accounts.views.sys_api.create_app_oauth_backend", return_value=backend) as patched:
        patched.backend = backend
        yield patched


def _stub_user_account(tenant_id: str | None) -> mock._patch:
    """让用凭证换用户身份这一步返回指定的租户。"""
    account = UserAccount(bk_username="alice", display_name="alice", tenant_id=tenant_id)
    return mock.patch.object(get_bkapp_oauth_backend_cls(), "resolve_user_account", return_value=account)


class TestTenantConsistency:
    """多租户下不允许跨租户借用用户身份"""

    @pytest.mark.parametrize("user_tenant_id", [None, "", "tenant-other"])
    def test_user_tenant_not_matching_is_denied(
        self,
        sys_aidev_api_client,
        ai_agent_app: "Application",
        stubbed_oauth_backend,
        user_tenant_id,
    ):
        """取不到用户租户或租户不一致时拒绝签发, 且不请求换票服务"""
        ai_agent_app.tenant_id = APP_TENANT_ID
        ai_agent_app.save(update_fields=["tenant_id"])
        header = get_bkapp_oauth_backend_cls().HEADER_KEY

        with (
            override_settings(ENABLE_MULTI_TENANT_MODE=True),
            _stub_user_account(user_tenant_id),
        ):
            resp = sys_aidev_api_client.get(_token_url(ai_agent_app.code), **{header: "credential"})

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "USER_APP_TENANT_MISMATCH"
        stubbed_oauth_backend.backend.fetch_token.assert_not_called()

    def test_same_tenant_is_allowed(self, sys_aidev_api_client, ai_agent_app: "Application", stubbed_oauth_backend):
        """用户与应用同租户时正常签发"""
        ai_agent_app.tenant_id = APP_TENANT_ID
        ai_agent_app.save(update_fields=["tenant_id"])
        header = get_bkapp_oauth_backend_cls().HEADER_KEY

        with (
            override_settings(ENABLE_MULTI_TENANT_MODE=True),
            _stub_user_account(APP_TENANT_ID),
        ):
            resp = sys_aidev_api_client.get(_token_url(ai_agent_app.code), **{header: "credential"})

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        assert resp.json()["access_token"] == ACCESS_TOKEN


class TestAuditRecord:
    """审计记录对应用所有成员可见, 不能写入可用的令牌"""

    def test_audit_excludes_token_payload(
        self, sys_aidev_api_client, ai_agent_app: "Application", stubbed_oauth_backend
    ):
        """签发成功后审计只保留元数据, 不包含 access_token / refresh_token"""
        header = get_bkapp_oauth_backend_cls().HEADER_KEY

        with _stub_user_account(None):
            resp = sys_aidev_api_client.get(_token_url(ai_agent_app.code), **{header: "credential"})

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        # 接口响应本身仍要返回真实令牌
        assert resp.json()["access_token"] == ACCESS_TOKEN

        record = AppOperationRecord.objects.get(app_code=ai_agent_app.code, target=OperationTarget.ACCESS_TOKEN)
        stored = str(record.data_after)
        assert ACCESS_TOKEN not in stored
        assert REFRESH_TOKEN not in stored
        # 仍然可以追溯签发环境与有效期
        assert record.data_after["data"] == {"env_name": "prod", "expires_in": EXPIRES_IN}
