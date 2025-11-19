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
    def url(self, bk_app):
        """生成测试 URL"""
        return reverse("plat_mgt.applications.processes.resource", kwargs={"app_code": bk_app.code})

    def test_list_resource_with_not_deploy(self, plat_mgt_api_client, bk_app, url):
        """测试列出应用进程资源, 没有部署过的应用"""
        response = plat_mgt_api_client.get(url)
        assert response.status_code == 200
        assert response.data == []

    def test_list_resource(self, plat_mgt_api_client, bk_app: Application, bk_module, url):
        """测试列出应用进程资源"""
        # 创建进程规格
        proc_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name="web", plan_name="default", tenant_id="default"
        )

        # 创建环境覆盖
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.STAG,
            plan_name="default",
            tenant_id="default",
        )
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.PROD,
            admin_res_config={
                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                "requests": {"cpu": "100m", "memory": "256Mi"},
            },
            tenant_id="default",
        )

        response = plat_mgt_api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1

        module_data = response.data[0]
        assert module_data["module_name"] == bk_module.name
        assert len(module_data["processes"]) == 1

        process_data = module_data["processes"][0]
        assert process_data["name"] == "web"
        assert "env_overlays" in process_data

        # 验证环境覆盖
        assert process_data["env_overlays"]["stag"]["plan_name"] == "default"
        assert process_data["env_overlays"]["prod"]["plan_name"] == "custom"
        assert process_data["env_overlays"]["prod"]["resources"] == {
            "limits": {"cpu": "2000m", "memory": "1024Mi"},
            "requests": {"cpu": "100m", "memory": "256Mi"},
        }

    def test_update_resource_source_origin_forbidden(self, plat_mgt_api_client, bk_app: Application, bk_module, url):
        """测试更新进程资源限制时,source_origin 不支持修改的场景"""
        # 设置为不支持的 source_origin
        bk_module.source_origin = SourceOrigin.AUTHORIZED_VCS.value
        bk_module.save(update_fields=["source_origin"])

        proc_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name="web", plan_name="default", tenant_id="default"
        )
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.STAG,
            plan_name="default",
            tenant_id="default",
        )

        # 更新请求
        data = {
            "module_name": bk_module.name,
            "source_origin": bk_module.source_origin,
            "processes": [
                {
                    "name": "web",
                    "env_overlays": {
                        "stag": {
                            "plan_name": "custom",
                            "resources": {
                                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                                "requests": {"cpu": "200m", "memory": "256Mi"},
                            },
                        }
                    },
                }
            ],
        }

        response = plat_mgt_api_client.put(url, data=data)
        assert response.status_code == 400

    def test_update_resource_success(self, plat_mgt_api_client, bk_app: Application, bk_module, url):
        """测试成功更新进程资源限制"""
        # 创建进程规格
        proc_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name="web", plan_name="default", tenant_id="default"
        )
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.STAG,
            plan_name="default",
            tenant_id="default",
        )

        # 更新请求
        data = {
            "module_name": bk_module.name,
            "source_origin": bk_module.source_origin,
            "processes": [
                {
                    "name": "web",
                    "env_overlays": {
                        "stag": {
                            "plan_name": "custom",
                            "resources": {
                                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                                "requests": {"cpu": "200m", "memory": "256Mi"},
                            },
                        }
                    },
                }
            ],
        }

        response = plat_mgt_api_client.put(url, data=data)
        assert response.status_code == 204

        # 验证数据库更新
        overlay = ProcessSpecEnvOverlay.objects.get(proc_spec=proc_spec, environment_name=AppEnvName.STAG)
        assert overlay.plan_name is None
        assert overlay.admin_res_config == {
            "limits": {"cpu": "2000m", "memory": "1024Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"},
        }

    def test_update_resource_multiple_processes(self, plat_mgt_api_client, bk_app: Application, bk_module, url):
        """测试批量更新多个进程资源限制"""
        # 创建多个进程规格
        web_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name="web", plan_name="default", tenant_id="default"
        )
        worker_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name="worker", plan_name="default", tenant_id="default"
        )

        ProcessSpecEnvOverlay.objects.create(
            proc_spec=web_spec, environment_name=AppEnvName.STAG, plan_name="default", tenant_id="default"
        )
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=worker_spec, environment_name=AppEnvName.STAG, plan_name="default", tenant_id="default"
        )

        # 批量更新
        data = {
            "module_name": bk_module.name,
            "source_origin": bk_module.source_origin,
            "processes": [
                {
                    "name": "web",
                    "env_overlays": {
                        "stag": {
                            "plan_name": "custom",
                            "resources": {
                                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                                "requests": {"cpu": "200m", "memory": "256Mi"},
                            },
                        }
                    },
                },
                {
                    "name": "worker",
                    "env_overlays": {
                        "stag": {
                            "plan_name": "custom",
                            "resources": {
                                "limits": {"cpu": "1000m", "memory": "512Mi"},
                                "requests": {"cpu": "200m", "memory": "256Mi"},
                            },
                        }
                    },
                },
            ],
        }

        response = plat_mgt_api_client.put(url, data=data)
        assert response.status_code == 204

        # 验证 web 进程
        web_overlay = ProcessSpecEnvOverlay.objects.get(proc_spec=web_spec, environment_name=AppEnvName.STAG)
        assert web_overlay.admin_res_config == {
            "limits": {"cpu": "2000m", "memory": "1024Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"},
        }

        # 验证 worker 进程
        worker_overlay = ProcessSpecEnvOverlay.objects.get(proc_spec=worker_spec, environment_name=AppEnvName.STAG)
        assert worker_overlay.admin_res_config == {
            "limits": {"cpu": "1000m", "memory": "512Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"},
        }

    def test_update_resource_with_plan_name(self, plat_mgt_api_client, bk_app: Application, bk_module, url):
        """测试更新为预设方案"""
        # 创建进程规格并设置自定义资源配置
        proc_spec = ModuleProcessSpec.objects.create(
            module=bk_module, name="web", plan_name="default", tenant_id="default"
        )
        ProcessSpecEnvOverlay.objects.create(
            proc_spec=proc_spec,
            environment_name=AppEnvName.STAG,
            admin_res_config={
                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                "requests": {"cpu": "200m", "memory": "256Mi"},
            },
            tenant_id="default",
        )

        # 更新为预设方案
        data = {
            "module_name": bk_module.name,
            "source_origin": bk_module.source_origin,
            "processes": [{"name": "web", "env_overlays": {"stag": {"plan_name": "default", "resources": None}}}],
        }

        response = plat_mgt_api_client.put(url, data=data)
        assert response.status_code == 204

        # 验证 admin_res_config 被清空
        overlay = ProcessSpecEnvOverlay.objects.get(proc_spec=proc_spec, environment_name=AppEnvName.STAG)
        assert overlay.plan_name == "default"
        assert overlay.admin_res_config is None

    def test_update_resource_create_overlay(self, plat_mgt_api_client, bk_app: Application, bk_module, url):
        """测试自动创建环境覆盖"""
        # 创建进程规格但不创建环境覆盖
        ModuleProcessSpec.objects.create(module=bk_module, name="web", plan_name="default", tenant_id="default")

        data = {
            "module_name": bk_module.name,
            "source_origin": bk_module.source_origin,
            "processes": [
                {
                    "name": "web",
                    "env_overlays": {
                        "stag": {
                            "plan_name": "custom",
                            "resources": {
                                "limits": {"cpu": "2000m", "memory": "1024Mi"},
                                "requests": {"cpu": "200m", "memory": "256Mi"},
                            },
                        }
                    },
                }
            ],
        }

        response = plat_mgt_api_client.put(url, data=data)
        assert response.status_code == 204

        # 验证自动创建了环境覆盖
        assert ProcessSpecEnvOverlay.objects.filter(
            proc_spec__module=bk_module, proc_spec__name="web", environment_name=AppEnvName.STAG
        ).exists()

    def test_update_resource_process_not_found(self, plat_mgt_api_client, bk_app: Application, bk_module, url):
        """测试更新不存在的进程"""
        data = {
            "module_name": bk_module.name,
            "source_origin": bk_module.source_origin,
            "processes": [
                {"name": "nonexistent", "env_overlays": {"stag": {"plan_name": "default", "resources": None}}}
            ],
        }

        response = plat_mgt_api_client.put(url, data=data)
        assert response.status_code == 404
        assert "nonexistent" in response.data["detail"]
