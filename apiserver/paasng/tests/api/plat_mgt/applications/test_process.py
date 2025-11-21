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

from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.constants import SourceOrigin

pytestmark = pytest.mark.django_db


class TestApplicationProcessViewSet:
    """测试平台管理 - 应用进程资源管理 API"""

    @pytest.fixture(autouse=True)
    def setup_module_source_origin(self, bk_module):
        """设置模块 source_origin 为允许修改的类型"""
        bk_module.source_origin = SourceOrigin.S_MART.value
        bk_module.save(update_fields=["source_origin"])

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

    def _create_process_with_overlay(self, bk_module, process_name="web", plan_name="default"):
        """创建进程规格和环境覆盖的辅助方法"""
        proc_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name=process_name, plan_name=plan_name, tenant_id="default"
        )
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.STAG,
            plan_name=plan_name,
            tenant_id="default",
        )
        return proc_spec

    def _create_process_with_custom_resources(self, bk_module, process_name="web"):
        """创建带自定义资源配置的进程规格"""
        proc_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name=process_name, plan_name="default", tenant_id="default"
        )
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.STAG,
            override_proc_res={
                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                "requests": {"cpu": "200m", "memory": "256Mi"},
            },
            tenant_id="default",
        )
        return proc_spec

    @staticmethod
    def _make_custom_resources_data(env_name="stag"):
        """生成自定义资源配置的请求数据"""
        return {
            "env_overlays": {
                env_name: {
                    "plan_name": None,
                    "resources": {
                        "limits": {"cpu": "2000m", "memory": "1024Mi"},
                        "requests": {"cpu": "200m", "memory": "256Mi"},
                    },
                }
            },
        }

    @staticmethod
    def _make_plan_name_data(plan_name="default", env_name="stag"):
        """生成预设方案的请求数据"""
        return {"env_overlays": {env_name: {"plan_name": plan_name}}}

    def test_list_resource_with_not_deploy(self, plat_mgt_api_client, list_url):
        """测试列出模块进程资源, 没有部署过的模块"""
        response = plat_mgt_api_client.get(list_url)
        assert response.status_code == 200
        assert response.data["processes"] == []

    def test_list_resource(self, plat_mgt_api_client, bk_app: Application, bk_module, list_url):
        """测试列出模块进程资源"""
        # 创建进程规格
        proc_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name="web", plan_name="default", tenant_id="default"
        )

        # 创建环境覆盖
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.STAG,
            plan_name="default",
        )
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.PROD,
            override_proc_res={
                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                "requests": {"cpu": "100m", "memory": "256Mi"},
            },
        )

        response = plat_mgt_api_client.get(list_url)
        assert response.status_code == 200
        assert response.data["module_name"] == bk_module.name
        assert len(response.data["processes"]) == 1

        process_data = response.data["processes"][0]
        assert process_data["name"] == "web"
        assert "env_overlays" in process_data

        # 验证环境覆盖
        assert process_data["env_overlays"]["stag"]["plan_name"] == "default"
        assert process_data["env_overlays"]["prod"]["plan_name"] is None
        assert process_data["env_overlays"]["prod"]["resources"] == {
            "limits": {"cpu": "2000m", "memory": "1024Mi"},
            "requests": {"cpu": "100m", "memory": "256Mi"},
        }

    def test_update_resource_source_origin_forbidden(
        self, plat_mgt_api_client, bk_app: Application, bk_module, update_url
    ):
        """测试更新进程资源限制时,source_origin 不支持修改的场景"""
        # 设置为不支持的 source_origin
        bk_module.source_origin = SourceOrigin.AUTHORIZED_VCS.value
        bk_module.save(update_fields=["source_origin"])

        self._create_process_with_overlay(bk_module)

        response = plat_mgt_api_client.put(update_url("web"), data=self._make_custom_resources_data())
        assert response.status_code == 400

    def test_update_resource_success(self, plat_mgt_api_client, bk_app: Application, bk_module, update_url, list_url):
        """测试成功更新进程资源限制"""
        self._create_process_with_overlay(bk_module)

        response = plat_mgt_api_client.put(update_url("web"), data=self._make_custom_resources_data())
        assert response.status_code == 204

        # 通过 API 验证更新结果
        response = plat_mgt_api_client.get(list_url)
        assert response.status_code == 200

        process_data = response.data["processes"][0]
        assert process_data["name"] == "web"
        assert process_data["env_overlays"]["stag"]["plan_name"] is None
        assert process_data["env_overlays"]["stag"]["resources"] == {
            "limits": {"cpu": "2000m", "memory": "1024Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"},
        }

    def test_update_resource_with_plan_name(
        self, plat_mgt_api_client, bk_app: Application, bk_module, update_url, list_url
    ):
        """测试更新为预设方案"""
        self._create_process_with_custom_resources(bk_module)

        response = plat_mgt_api_client.put(update_url("web"), data=self._make_plan_name_data())
        assert response.status_code == 204

        # 通过 API 验证 override_proc_res 被清空
        response = plat_mgt_api_client.get(list_url)
        assert response.status_code == 200

        process_data = response.data["processes"][0]
        assert process_data["env_overlays"]["stag"]["plan_name"] == "default"
        assert process_data["env_overlays"]["stag"]["resources"] is None

    def test_update_resource_create_overlay(
        self, plat_mgt_api_client, bk_app: Application, bk_module, update_url, list_url
    ):
        """测试自动创建环境覆盖"""
        ModuleProcessSpec.objects.create(module=bk_module, name="web", plan_name="default", tenant_id="default")

        response = plat_mgt_api_client.put(update_url("web"), data=self._make_custom_resources_data())
        assert response.status_code == 204

        # 通过 API 验证环境覆盖已创建
        response = plat_mgt_api_client.get(list_url)
        assert response.status_code == 200

        process_data = response.data["processes"][0]
        assert process_data["env_overlays"]["stag"]["plan_name"] is None
        assert process_data["env_overlays"]["stag"]["resources"] is not None

    def test_update_resource_process_not_found(self, plat_mgt_api_client, bk_app: Application, bk_module, update_url):
        """测试更新不存在的进程"""
        response = plat_mgt_api_client.put(update_url("nonexistent"), data=self._make_plan_name_data())
        assert response.status_code == 404
        assert "nonexistent" in response.data["detail"]
