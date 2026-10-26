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
import uuid
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from rest_framework import status

from paasng.accessories.servicehub.services import ServiceInstanceObj
from paasng.core.tenant.user import DEFAULT_TENANT_ID

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application
    from paasng.platform.modules.models import Module

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SERVICE_ID = str(uuid.uuid4())


def _service_instance_url(app_code: str, module_name: str, service_id: str = SERVICE_ID) -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/services/{service_id}/"


@pytest.fixture()
def service_instance() -> ServiceInstanceObj:
    return ServiceInstanceObj(
        uuid=str(uuid.uuid4()),
        credentials={"username": "user", "password": "pwd"},
        config={"admin_url": "https://bkm.example.com/?space_uid=bksaas__ai-demo", "env": "stag"},
        create_time=datetime.datetime(2024, 1, 1),
        tenant_id=DEFAULT_TENANT_ID,
    )


def _build_rel(service_instance: ServiceInstanceObj) -> mock.MagicMock:
    plan = mock.MagicMock()
    plan.name = "default-otel"
    plan.description = "otel service"

    rel = mock.MagicMock()
    rel.get_instance.return_value = service_instance
    rel.get_plan.return_value = plan
    return rel


@pytest.fixture()
def stubbed_service_mgr(service_instance: ServiceInstanceObj):
    with mock.patch("paasng.accessories.servicehub.views.mixed_service_mgr") as mgr:
        service_obj = mock.MagicMock()
        service_obj.uuid = SERVICE_ID

        mgr.get_or_404.return_value = service_obj
        mgr.module_is_bound_with.return_value = True
        mgr.list_provisioned_rels.return_value = [_build_rel(service_instance)]
        mgr.list_all_rels.return_value = [_build_rel(service_instance)]
        yield mgr


class TestSysGetServiceInstanceByModule:
    """应用态查询模块绑定的增强服务实例接口测试"""

    def test_success(
        self,
        sys_aidev_api_client,
        ai_agent_app: "Application",
        bk_module: "Module",
        service_instance: ServiceInstanceObj,
        stubbed_service_mgr,
    ):
        """AIDEV 可以查询 AI Agent 应用模块绑定的增强服务实例, 其中包含 admin_url"""
        resp = sys_aidev_api_client.get(_service_instance_url(ai_agent_app.code, bk_module.name))

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        body = resp.json()
        envs = list(bk_module.envs.values_list("environment", flat=True))
        assert body["count"] == len(envs)
        assert {r["environment"] for r in body["results"]} == set(envs)
        for result in body["results"]:
            assert result["service_instance"]["config"]["admin_url"] == service_instance.config["admin_url"]
            assert result["service_instance"]["credentials"] == '{"username": "user", "password": "pwd"}'

        resp = sys_aidev_api_client.get(_service_instance_url(ai_agent_app.code, bk_module.name))
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        assert resp.json()["count"] == len(bk_module.envs.all())

    def test_basic_maintainer_denied(
        self, sys_api_client, ai_agent_app: "Application", bk_module: "Module", stubbed_service_mgr
    ):
        """BASIC_MAINTAINER 拥有部分系统 API 权限, 但不能调用仅 AIDEV 可用的接口"""
        resp = sys_api_client.get(_service_instance_url(ai_agent_app.code, bk_module.name))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"
        stubbed_service_mgr.get_or_404.assert_not_called()

    def test_non_ai_agent_app_denied(
        self, sys_aidev_api_client, bk_app: "Application", bk_module: "Module", stubbed_service_mgr
    ):
        """对非 AI Agent 应用调用时返回 403"""
        assert bk_app.is_ai_agent_app is False
        resp = sys_aidev_api_client.get(_service_instance_url(bk_app.code, bk_module.name))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"
        stubbed_service_mgr.get_or_404.assert_not_called()

    def test_does_not_query_iam(
        self,
        sys_aidev_api_client,
        ai_agent_app: "Application",
        bk_module: "Module",
        stubbed_service_mgr,
    ):
        """应用态接口不查询 IAM 权限: AIDEV 加入成员后 IAM 存在延迟, 不能依赖用户态权限校验"""
        with mock.patch(
            "paasng.infras.accounts.permissions.application.check_application_perm"
        ) as check_application_perm:
            resp = sys_aidev_api_client.get(_service_instance_url(ai_agent_app.code, bk_module.name))

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        check_application_perm.assert_not_called()
        # 未绑定的 service 也不会触发用户态的模块/应用权限校验
        stubbed_service_mgr.module_is_bound_with.assert_called_once()
