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


import pytest
from django.urls import reverse

from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.modules.constants import SourceOrigin

pytestmark = pytest.mark.django_db


class TestApplicationProcessViewSet:
    """测试平台管理 - 应用进程资源管理 API"""

    @pytest.fixture(autouse=True)
    def setup_module_source_origin(self, bk_module):
        """设置模块 source_origin 为允许修改的类型"""
        bk_module.source_origin = SourceOrigin.S_MART.value
        bk_module.save(update_fields=["source_origin"])

    @pytest.fixture(autouse=True)
    def setup_process_spec_env_overlay(self, bk_module):
        """确保模块存在进程规格和环境覆盖"""
        proc_spec, _ = ModuleProcessSpec.objects.get_or_create(
            module=bk_module, name="web", defaults={"plan_name": "default", "tenant_id": "default"}
        )
        ProcessSpecEnvOverlay.objects.get_or_create(proc_spec=proc_spec, environment_name="stag")
        ProcessSpecEnvOverlay.objects.get_or_create(proc_spec=proc_spec, environment_name="prod")

    @pytest.fixture()
    def list_url(self, bk_app, bk_module):
        """生成列表 URL"""
        return reverse(
            "plat_mgt.applications.processes.list",
            kwargs={"app_code": bk_app.code, "module_name": bk_module.name},
        )

    @pytest.fixture()
    def update_url(self, bk_app, bk_module):
        """生成更新 URL 工厂函数"""

        def _make_url(process_name):
            return reverse(
                "plat_mgt.applications.processes.update",
                kwargs={"app_code": bk_app.code, "module_name": bk_module.name, "process_name": process_name},
            )

        return _make_url

    @staticmethod
    def _make_update_data(env_name="stag", override_proc_res=None):
        """生成更新请求数据"""
        if override_proc_res is None:
            # 默认使用自定义资源
            override_proc_res = {
                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                "requests": {"cpu": "200m", "memory": "256Mi"},
            }

        return {"env_overlays": {env_name: {"override_proc_res": override_proc_res}}}

    def _get_process_data(self, plat_mgt_api_client, list_url, process_name="web"):
        """获取指定进程的数据"""
        response = plat_mgt_api_client.get(list_url)
        assert response.status_code == 200
        for proc in response.data["processes"]:
            if proc["name"] == process_name:
                return proc
        return None

    def test_list_resource_success(self, plat_mgt_api_client, bk_module, list_url):
        """测试获取模块进程资源配置"""
        response = plat_mgt_api_client.get(list_url)
        assert response.status_code == 200
        assert response.data["module_name"] == bk_module.name
        assert response.data["source_origin"] == bk_module.source_origin
        assert len(response.data["processes"]) == 1

        process = response.data["processes"][0]
        assert process["name"] == "web"
        assert "env_overlays" in process

    def test_update_resource_unsupported_source_origin(self, plat_mgt_api_client, bk_module, update_url):
        """测试不支持的源码类型无法修改资源配置"""
        bk_module.source_origin = SourceOrigin.AUTHORIZED_VCS.value
        bk_module.save(update_fields=["source_origin"])

        response = plat_mgt_api_client.put(update_url("web"), data=self._make_update_data())
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "override_proc_res",
        [
            {"plan": "4C2G"},
            {"limits": {"cpu": "2000m", "memory": "1024Mi"}, "requests": {"cpu": "200m", "memory": "256Mi"}},
        ],
        ids=["quota_plan", "custom_override_proc_res"],
    )
    def test_update_resource_success(self, plat_mgt_api_client, bk_module, update_url, list_url, override_proc_res):
        """测试更新进程资源配置 - 配额方案/自定义资源"""
        data = self._make_update_data(override_proc_res=override_proc_res)
        response = plat_mgt_api_client.put(update_url("web"), data=data)
        assert response.status_code == 204

        process_data = self._get_process_data(plat_mgt_api_client, list_url)
        assert process_data["env_overlays"]["stag"]["override_proc_res"] == override_proc_res

    def test_update_resource_process_not_found(self, plat_mgt_api_client, update_url):
        """测试更新不存在的进程"""
        response = plat_mgt_api_client.put(update_url("nonexistent"), data=self._make_update_data())
        assert response.status_code == 404
        assert "nonexistent" in response.data["detail"]

    def test_update_resource_invalid_environment(self, plat_mgt_api_client, update_url):
        """测试指定无效环境名称"""
        data = self._make_update_data(env_name="invalid_env")
        response = plat_mgt_api_client.put(update_url("web"), data=data)
        assert response.status_code == 400
        assert response.data["code"] == "VALIDATION_ERROR"

    @pytest.mark.parametrize(
        ("limits", "requests", "expected_status"),
        [
            ({"cpu": "1000m", "memory": "512Mi"}, {"cpu": "1000m", "memory": "512Mi"}, 204),
            ({"cpu": "2000m", "memory": "1024Mi"}, {"cpu": "1000m", "memory": "512Mi"}, 204),
            ({"cpu": "1000m", "memory": "1024Mi"}, {"cpu": "2000m", "memory": "256Mi"}, 400),
            ({"cpu": "2000m", "memory": "256Mi"}, {"cpu": "2000m", "memory": "512Mi"}, 400),
        ],
        ids=["equal", "limits_greater", "cpu_invalid", "memory_invalid"],
    )
    def test_update_resource_quota_validation(
        self, plat_mgt_api_client, update_url, list_url, limits, requests, expected_status
    ):
        """测试资源配额校验 - limits 必须 >= requests"""
        override_proc_res = {"limits": limits, "requests": requests}
        data = self._make_update_data(override_proc_res=override_proc_res)
        response = plat_mgt_api_client.put(update_url("web"), data=data)
        assert response.status_code == expected_status

        if expected_status == 204:
            process_data = self._get_process_data(plat_mgt_api_client, list_url)
            assert process_data["env_overlays"]["stag"]["override_proc_res"] == override_proc_res
        else:
            assert response.data["code"] == "VALIDATION_ERROR"

    def test_list_quota_plans_success(self, plat_mgt_api_client):
        """测试获取可用资源配额方案列表"""
        url = reverse("plat_mgt.process.list_quota_plans")
        response = plat_mgt_api_client.get(url)

        assert response.status_code == 200
        assert isinstance(response.data, list)
        for plan in response.data:
            assert "name" in plan
            assert "limits" in plan
            assert "requests" in plan
            assert isinstance(plan["limits"], dict)
            assert isinstance(plan["requests"], dict)
