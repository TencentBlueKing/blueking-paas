# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import pytest
from django_dynamic_fixture import G

from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.models import BuildConfig

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


class TestModuleProcessSpecViewSet:
    @pytest.fixture(autouse=True)
    def setup(self, bk_cnative_app, bk_module):
        cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
        cfg.build_method = RuntimeType.CUSTOM_IMAGE
        cfg.image_repository = "example.com/foo"
        cfg.save()

    @pytest.fixture
    def web(self, bk_module):
        return G(
            ModuleProcessSpec,
            module=bk_module,
            name="web",
            command=["python"],
            args=["-m", "http.server"],
            port=8000,
        )

    @pytest.fixture
    def celery_worker(self, bk_module):
        return G(ModuleProcessSpec, module=bk_module, name="worker", command=["celery"])

    def test_retrieve(self, api_client, bk_cnative_app, bk_module, web, celery_worker):
        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.get(url)
        data = resp.json()
        metadata = data["metadata"]
        proc_specs = data["proc_specs"]
        assert metadata["allow_multiple_image"] is False
        assert len(proc_specs) == 2
        assert proc_specs[0]["name"] == "web"
        assert proc_specs[0]["image"] == "example.com/foo"
        assert proc_specs[0]["command"] == ["python"]
        assert proc_specs[0]["args"] == ["-m", "http.server"]

        assert proc_specs[1]["name"] == "worker"
        assert proc_specs[1]["image"] == "example.com/foo"
        assert proc_specs[1]["command"] == ["celery"]
        assert proc_specs[1]["args"] is None

    @pytest.fixture
    def web_v1alpha1(self, web):
        web.image = "python:latest"
        web.save()
        return web

    def test_retrieve_v1alpha1(self, api_client, bk_cnative_app, bk_module, web_v1alpha1, celery_worker):
        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.get(url)
        data = resp.json()
        metadata = data["metadata"]
        proc_specs = data["proc_specs"]

        assert metadata["allow_multiple_image"] is True
        assert len(proc_specs) == 2
        assert proc_specs[0]["name"] == "web"
        assert proc_specs[0]["image"] == "python:latest"
        assert proc_specs[0]["command"] == ["python"]
        assert proc_specs[0]["args"] == ["-m", "http.server"]

        assert proc_specs[1]["name"] == "worker"
        assert proc_specs[1]["image"] == "example.com/foo"
        assert proc_specs[1]["command"] == ["celery"]
        assert proc_specs[1]["args"] is None

    def test_save(self, api_client, bk_cnative_app, bk_module, web, celery_worker):
        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        request_data = [
            {
                "name": "web",
                # 设置 image 字段不会生效
                "image": "python:latest",
                "command": ["python", "-m"],
                "args": ["http.server"],
                "port": 5000,
                "env_overlay": {
                    "stag": {
                        "environment_name": "stag",
                        "plan_name": "default",
                        "target_replicas": 2,
                    }
                },
            },
            {
                "name": "beat",
                "command": ["python", "-m"],
                "args": ["celery", "beat"],
                "env_overlay": {
                    "stag": {
                        "environment_name": "stag",
                        "plan_name": "default",
                        "target_replicas": 1,
                    },
                    "prod": {
                        "environment_name": "stag",
                        "plan_name": "default",
                        "target_replicas": 1,
                        "autoscaling": True,
                        "scaling_config": {
                            "min_replicas": 1,
                            "max_replicas": 5,
                            "metrics": [{"type": "Resource", "metric": "cpuUtilization", "value": "70%"}],
                        },
                    },
                },
            },
        ]
        resp = api_client.post(url, data=request_data)
        data = resp.json()
        metadata = data["metadata"]
        proc_specs = data["proc_specs"]

        assert ModuleProcessSpec.objects.filter(module=bk_module).count() == 2
        assert metadata["allow_multiple_image"] is False
        assert len(proc_specs) == 2
        assert proc_specs[0]["name"] == "web"
        assert proc_specs[0]["image"] == "example.com/foo"
        assert proc_specs[0]["command"] == ["python", "-m"]
        assert proc_specs[0]["args"] == ["http.server"]
        assert proc_specs[0]["env_overlay"]["stag"]["target_replicas"] == 2

        assert proc_specs[1]["name"] == "beat"
        assert proc_specs[1]["image"] == "example.com/foo"
        assert proc_specs[1]["command"] == ["python", "-m"]
        assert proc_specs[1]["args"] == ["celery", "beat"]
        assert proc_specs[1]["env_overlay"]["prod"]["scaling_config"] == {
            "min_replicas": 1,
            "max_replicas": 5,
            "metrics": [{"type": "Resource", "metric": "cpuUtilization", "value": "70%"}],
            "policy": "default",
        }
        assert ModuleProcessSpec.objects.get(module=bk_module, name="beat").get_scaling_config("prod") == {
            "minReplicas": 1,
            "maxReplicas": 5,
            "metrics": [{"type": "Resource", "metric": "cpuUtilization", "value": "70%"}],
            "policy": "default",
        }

    def test_save_v1alpha1(self, api_client, bk_cnative_app, bk_module, web_v1alpha1, celery_worker):
        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        request_data = [
            {
                "name": "web",
                "image": "python:latest",
                "command": ["python", "-m"],
                "args": ["http.server"],
                "port": 5000,
            }
        ]
        resp = api_client.post(url, data=request_data)
        data = resp.json()
        metadata = data["metadata"]
        proc_specs = data["proc_specs"]

        assert ModuleProcessSpec.objects.filter(module=bk_module).count() == 1
        assert metadata["allow_multiple_image"] is True
        assert len(proc_specs) == 1
        assert proc_specs[0]["name"] == "web"
        assert proc_specs[0]["image"] == "python:latest"
        assert proc_specs[0]["command"] == ["python", "-m"]
        assert proc_specs[0]["args"] == ["http.server"]
