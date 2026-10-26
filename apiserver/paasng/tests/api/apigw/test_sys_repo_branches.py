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


import datetime
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from rest_framework import status

from paasng.platform.sourcectl.constants import VersionType
from paasng.platform.sourcectl.models import AlternativeVersion

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application
    from paasng.platform.modules.models import Module

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _branches_url(app_code: str, module_name: str) -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/repo/branches/"


@pytest.fixture()
def ai_agent_app(bk_app: "Application") -> "Application":
    bk_app.is_ai_agent_app = True
    bk_app.save(update_fields=["is_ai_agent_app"])
    return bk_app


@pytest.fixture()
def stubbed_version_service():
    alternative_version = AlternativeVersion(
        name="master",
        type=VersionType.BRANCH.value,
        revision="31736e690ba0bfa7a81d3730ed6544b3566b3f19",
        url="http://git.example.com/ai-demo.git",
        last_update=datetime.datetime(2024, 9, 10, 16, 48, 24),
        message="init repo",
    )
    with mock.patch("paasng.platform.sourcectl.views.get_version_service") as get_version_service:
        get_version_service.return_value.list_alternative_versions.return_value = [alternative_version]
        yield get_version_service


class TestSysGetRepoBranches:
    """应用态获取代码分支接口测试"""

    def test_success(
        self,
        sys_aidev_api_client,
        ai_agent_app: "Application",
        bk_module: "Module",
        stubbed_version_service,
    ):
        """AIDEV 可以查询 AI Agent 应用模块的分支信息, 使用模块 owner 的凭证"""
        resp = sys_aidev_api_client.get(_branches_url(ai_agent_app.code, bk_module.name))

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        body = resp.json()
        assert len(body["results"]) == 1
        assert body["results"][0]["name"] == "master"
        assert body["results"][0]["revision"] == "31736e690ba0bfa7a81d3730ed6544b3566b3f19"
        assert stubbed_version_service.call_args.kwargs["operator"] == bk_module.owner

    def test_basic_maintainer_denied(
        self, sys_api_client, ai_agent_app: "Application", bk_module: "Module", stubbed_version_service
    ):
        """BASIC_MAINTAINER 拥有部分系统 API 权限, 但不能调用仅 AIDEV 可用的接口"""
        resp = sys_api_client.get(_branches_url(ai_agent_app.code, bk_module.name))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"
        stubbed_version_service.assert_not_called()

    def test_non_ai_agent_app_denied(
        self, sys_aidev_api_client, bk_app: "Application", bk_module: "Module", stubbed_version_service
    ):
        """对非 AI Agent 应用调用时返回 403"""
        assert bk_app.is_ai_agent_app is False
        resp = sys_aidev_api_client.get(_branches_url(bk_app.code, bk_module.name))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"
        stubbed_version_service.assert_not_called()
