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

from unittest import mock

import pytest
from rest_framework import status

from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.core.tenant.constants import AppTenantMode
from paasng.platform.applications.models import Application

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

FAKE_DEPLOY_INFO = {
    "stag": {"deployed": True, "url": "http://ai-demo-stag.example.com"},
    "prod": {"deployed": False, "url": ""},
}


def _detail_url(app_code: str) -> str:
    return f"/sys/api/bkapps/applications/{app_code}/"


@pytest.fixture(autouse=True)
def patch_exposed_links():
    with mock.patch(
        "paasng.platform.applications.views.sys_api.get_exposed_links", return_value=FAKE_DEPLOY_INFO
    ) as mocked:
        yield mocked


@pytest.fixture()
def single_tenant_app(ai_agent_app: Application) -> Application:
    ai_agent_app.app_tenant_mode = AppTenantMode.SINGLE.value
    ai_agent_app.app_tenant_id = "t1"
    ai_agent_app.save(update_fields=["app_tenant_mode", "app_tenant_id"])
    return ai_agent_app


class TestSysGetAppInfo:
    """应用态查询应用信息接口测试"""

    def test_get_success(self, sys_aidev_api_client, ai_agent_app: Application, patch_exposed_links):
        """AIDEV 可以查询 AI Agent 应用的信息, 部署模式与访问地址"""
        resp = sys_aidev_api_client.get(_detail_url(ai_agent_app.code))

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        app_data = resp.json()["application"]
        assert app_data["code"] == ai_agent_app.code
        assert app_data["deploy_policy"] == ai_agent_app.deploy_policy
        assert app_data["is_ai_agent_app"] is True
        assert app_data["deploy_info"] == FAKE_DEPLOY_INFO
        assert app_data["preferred_prod_url"] is None

        # 应用市场配置了独立域名时, preferred_prod_url 应返回该域名
        market_config = ai_agent_app.market_config
        market_config.enabled = True
        market_config.source_url_type = ProductSourceUrlType.CUSTOM_DOMAIN.value
        market_config.custom_domain_url = "https://custom.domain.example.com"
        market_config.save()
        resp = sys_aidev_api_client.get(_detail_url(ai_agent_app.code))
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        assert resp.json()["application"]["preferred_prod_url"] == market_config.custom_domain_url

    def test_basic_maintainer_denied(self, sys_api_client, ai_agent_app: Application, patch_exposed_links):
        """BASIC_MAINTAINER 拥有部分系统 API 权限, 但不能调用仅 AIDEV 可用的接口"""
        resp = sys_api_client.get(_detail_url(ai_agent_app.code))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"
        patch_exposed_links.assert_not_called()

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app: Application, patch_exposed_links):
        """对非 AI Agent 应用调用时返回 403"""
        assert bk_app.is_ai_agent_app is False

        resp = sys_aidev_api_client.get(_detail_url(bk_app.code))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"
        patch_exposed_links.assert_not_called()
