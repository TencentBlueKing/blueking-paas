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

from pathlib import Path

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paasng.platform.bkapp_model.entities import AutoscalingConfig, Metric, ProcService
from paasng.platform.bkapp_model.entities.components import Component
from paasng.platform.bkapp_model.models import (
    ModuleProcessSpec,
    ObservabilityConfig,
    ProcessSpecEnvOverlay,
)
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.modules.models import BuildConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(autouse=True)
def _setup(bk_cnative_app, bk_module):
    cfg = BuildConfig.objects.get_or_create_by_module(bk_module)
    cfg.build_method = RuntimeType.CUSTOM_IMAGE
    cfg.image_repository = "example.com/foo"
    cfg.save()


class TestModuleProcessSpecViewSet:
    @pytest.fixture()
    def web(self, bk_module):
        return G(
            ModuleProcessSpec,
            module=bk_module,
            name="web",
            proc_command="python -m http.server",
            command=["python"],
            args=["-m", "http.server"],
            port=8000,
            components=[
                Component(name="env_overlay", version="v2"),
            ],
        )

    @pytest.fixture()
    def celery_worker(self, bk_module):
        return G(ModuleProcessSpec, module=bk_module, name="worker", command=["celery"])

    def test_retrieve(self, api_client, bk_cnative_app, bk_module, web, celery_worker):
        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.get(url)
        data = resp.json()
        proc_specs = data["proc_specs"]
        assert len(proc_specs) == 2
        assert proc_specs[0]["name"] == "web"
        assert proc_specs[0]["image"] == "example.com/foo"
        assert proc_specs[0]["proc_command"] == "python -m http.server"
        assert proc_specs[0]["command"] == ["python"]
        assert proc_specs[0]["args"] == ["-m", "http.server"]
        assert proc_specs[0]["env_overlay"]["stag"]["scaling_config"] == {
            "min_replicas": 1,
            "max_replicas": 1,
            "metrics": [{"type": "Resource", "metric": "cpuUtilization", "value": "85"}],
            "policy": "default",
        }
        assert proc_specs[0]["services"] is None
        assert proc_specs[0]["components"] == [
            {"name": "env_overlay", "version": "v2", "properties": {}},
        ]

        assert proc_specs[1]["name"] == "worker"
        assert proc_specs[1]["proc_command"] is None
        assert proc_specs[1]["image"] == "example.com/foo"
        assert proc_specs[1]["command"] == ["celery"]
        assert proc_specs[1]["args"] == []
        assert proc_specs[1]["services"] is None

    def test_save(self, api_client, bk_cnative_app, bk_module, web, celery_worker):
        G(
            ProcessSpecEnvOverlay,
            proc_spec=web,
            environment_name="stag",
            autoscaling=True,
            scaling_config={
                "min_replicas": 1,
                "max_replicas": 5,
                "policy": "default",
            },
        )
        assert web.get_autoscaling("stag")
        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        probes_cfg = {
            "liveness": {
                "exec": {"command": ["/bin/bash", "-c", "echo hello"]},
                "http_get": None,
                "tcp_socket": None,
                "initial_delay_seconds": 5,
                "timeout_seconds": 5,
                "period_seconds": 5,
                "success_threshold": 1,
                "failure_threshold": 3,
            },
            "readiness": {
                "exec": None,
                "tcp_socket": None,
                "http_get": {
                    "port": 8080,
                    "host": "bk.example.com",
                    "path": "/healthz",
                    "http_headers": [{"name": "XXX", "value": "YYY"}],
                    "scheme": "HTTPS",
                },
                "initial_delay_seconds": 15,
                "timeout_seconds": 60,
                "period_seconds": 10,
                "success_threshold": 1,
                "failure_threshold": 5,
            },
            "startup": {
                "exec": None,
                "http_get": None,
                "tcp_socket": {"port": 8080, "host": "bk.example.com"},
                "initial_delay_seconds": 5,
                "timeout_seconds": 15,
                "period_seconds": 2,
                "success_threshold": 1,
                "failure_threshold": 5,
            },
        }
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
                        "plan_name": "default",
                        "target_replicas": 2,
                        "autoscaling": False,
                    }
                },
                "probes": probes_cfg,
            },
            {
                "name": "beat",
                "command": ["python", "-m"],
                "args": ["celery", "beat"],
                "env_overlay": {
                    "stag": {
                        "plan_name": "default",
                        "target_replicas": 1,
                    },
                    "prod": {
                        "plan_name": "default",
                        "target_replicas": 1,
                        "autoscaling": True,
                        "scaling_config": {
                            "min_replicas": 1,
                            "max_replicas": 5,
                            # NOTE: The metrics field will be ignored by the backend
                            "metrics": [{"type": "Resource", "metric": "cpuUtilization", "value": "70"}],
                        },
                    },
                },
                "probes": {
                    "liveness": None,
                    "readiness": None,
                    "startup": None,
                },
            },
        ]
        resp = api_client.post(url, data={"proc_specs": request_data})
        data = resp.json()

        proc_specs = data["proc_specs"]

        assert ModuleProcessSpec.objects.filter(module=bk_module).count() == 2
        assert len(proc_specs) == 2

        assert proc_specs[0]["name"] == "web"
        assert proc_specs[0]["image"] == "example.com/foo"
        assert proc_specs[0]["command"] == ["python", "-m"]
        assert proc_specs[0]["args"] == ["http.server"]
        assert proc_specs[0]["port"] == 5000
        assert proc_specs[0]["env_overlay"]["stag"]["target_replicas"] == 2
        assert not proc_specs[0]["env_overlay"]["stag"]["autoscaling"]
        assert proc_specs[0]["probes"] == probes_cfg

        assert proc_specs[1]["name"] == "beat"
        assert proc_specs[1]["image"] == "example.com/foo"
        assert proc_specs[1]["command"] == ["python", "-m"]
        assert proc_specs[1]["args"] == ["celery", "beat"]
        assert proc_specs[1]["env_overlay"]["prod"]["scaling_config"] == {
            "min_replicas": 1,
            "max_replicas": 5,
            "metrics": [{"type": "Resource", "metric": "cpuUtilization", "value": "85"}],
            "policy": "default",
        }
        assert proc_specs[1]["probes"] == {"liveness": None, "readiness": None, "startup": None}

        spec_obj = ModuleProcessSpec.objects.get(module=bk_module, name="beat")
        assert spec_obj.get_scaling_config("prod") == AutoscalingConfig(
            min_replicas=1,
            max_replicas=5,
            policy="default",
        )
        assert spec_obj.probes == {"liveness": None, "readiness": None, "startup": None}
        assert spec_obj.probes.liveness is None


class TestModuleProcessSpecWithProcServicesViewSet:
    @pytest.fixture()
    def web(self, bk_module):
        return G(
            ModuleProcessSpec,
            module=bk_module,
            name="web",
            command=["python"],
            args=["-m", "http.server"],
            port=8000,
            services=[
                ProcService(name="web", target_port=8000, exposed_type={"name": "bk/http"}),
                ProcService(name="backend", target_port=8001, port=80),
            ],
        )

    @pytest.mark.parametrize(
        ("proc_services", "expected_status_code", "expected_detail_str"),
        [
            (None, 200, ""),
            ([{"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/http"}}], 200, ""),
            ([{"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/grpc"}}], 200, ""),
            # invalid exposed_type
            ([{"name": "web", "target_port": 5000, "exposed_type": {"name": "foo/http"}}], 400, "不是合法选项"),
            ([{"name": "web"}], 400, "services.target_port: 该字段是必填项"),
            # duplicate name
            (
                [{"name": "web", "target_port": 5000}, {"name": "web", "target_port": 5001}],
                400,
                "duplicate service name: web",
            ),
            # duplicate target_port
            (
                [{"name": "web", "target_port": 5000}, {"name": "worker", "target_port": 5000}],
                400,
                "duplicate target_port: 5000",
            ),
        ],
    )
    def test_validate(
        self, api_client, bk_cnative_app, bk_module, proc_services, expected_status_code, expected_detail_str
    ):
        request_data = [
            {
                "name": "web",
                "image": "python:latest",
                "command": ["python", "-m"],
                "args": ["http.server"],
                "services": proc_services,
            }
        ]

        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.post(url, data={"proc_specs": request_data})
        assert resp.status_code == expected_status_code
        assert expected_detail_str in resp.data.get("detail", "")

    @pytest.mark.parametrize(
        ("request_services", "exposed_type"),
        [
            # 单个进程内的 bk/http 重复
            (
                [
                    [
                        {"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/http"}},
                        {"name": "backend", "target_port": 5001, "exposed_type": {"name": "bk/http"}},
                    ]
                ],
                "bk/http",
            ),
            # 多个进程间的 bk/http 重复
            (
                [
                    [
                        {"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/http"}},
                    ],
                    [
                        {"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/http"}},
                    ],
                ],
                "bk/http",
            ),
            # 多个进程间的 bk/grpc 重复
            (
                [
                    [
                        {"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/grpc"}},
                    ],
                    [
                        {"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/grpc"}},
                    ],
                ],
                "bk/grpc",
            ),
        ],
    )
    def test_validate_duplicated_exposed_type(
        self, api_client, bk_cnative_app, bk_module, request_services, exposed_type
    ):
        """测试 proc services 中含有重复 exposed type 的场景"""
        request_proc_specs = []
        for services in request_services:
            request_proc_specs.append(
                {
                    "name": "foo",
                    "image": "python:latest",
                    "command": ["python", "-m"],
                    "args": ["http.server"],
                    "services": services,
                }
            )

        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.post(url, data={"proc_specs": request_proc_specs})
        assert resp.status_code == 400
        assert f"exposed_type {exposed_type} is duplicated in an app module" in resp.data.get("detail", "")

    @pytest.mark.parametrize(
        "request_services",
        [
            # 单个进程内配置了不同的 exposed type
            (
                [
                    [
                        {"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/http"}},
                        {"name": "backend", "target_port": 5001, "exposed_type": {"name": "bk/grpc"}},
                    ],
                ]
            ),
            # 不同的进程配置了不同的 exposed type
            (
                [
                    [
                        {"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/http"}},
                    ],
                    [
                        {"name": "web", "target_port": 5000, "exposed_type": {"name": "bk/grpc"}},
                    ],
                ]
            ),
        ],
    )
    def test_validate_multiple_exposed_type(self, api_client, bk_cnative_app, bk_module, web, request_services):
        """测试 proc services 中含有多个 exposed type 的场景"""
        request_proc_specs = []
        for services in request_services:
            request_proc_specs.append(
                {
                    "name": "foo",
                    "image": "python:latest",
                    "command": ["python", "-m"],
                    "args": ["http.server"],
                    "services": services,
                }
            )

        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.post(url, data={"proc_specs": request_proc_specs})
        assert resp.status_code == 400
        assert "setting multiple exposed_types in an app module is not supported" in resp.data.get("detail", "")

    @pytest.mark.parametrize("exposed_type", ["bk/http", "bk/grpc"])
    def test_save(self, api_client, bk_cnative_app, bk_module, web, exposed_type):
        request_data = [
            {
                "name": "web",
                "image": "python:latest",
                "command": ["python", "-m"],
                "args": ["http.server"],
                "port": 5000,
                "services": [
                    {"name": "web", "target_port": "${PORT}", "port": 80, "exposed_type": {"name": exposed_type}},
                    {"name": "backend", "target_port": 5001},
                ],
            },
            {
                "name": "celery",
                "image": "python:latest",
                "command": ["celery", "-l"],
                "args": ["info"],
                "port": 5000,
            },
        ]

        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.post(url, data={"proc_specs": request_data})
        data = resp.json()

        proc_specs = data["proc_specs"]
        assert proc_specs[0]["services"] == [
            {
                "name": "web",
                "target_port": settings.CONTAINER_PORT,
                "port": 80,
                "exposed_type": {"name": exposed_type},
                "protocol": "TCP",
            },
            {"name": "backend", "target_port": 5001, "port": 5001, "exposed_type": None, "protocol": "TCP"},
        ]
        assert proc_specs[1]["services"] is None

        web_process_spec = ModuleProcessSpec.objects.get(module=bk_module, name="web")
        assert web_process_spec.services[0].target_port == "${PORT}"
        assert web_process_spec.services[0].port == 80
        assert web_process_spec.services[0].exposed_type.name == exposed_type

        celery_process_spec = ModuleProcessSpec.objects.get(module=bk_module, name="celery")
        assert celery_process_spec.services is None

    def test_retrieve(self, api_client, bk_cnative_app, bk_module, web):
        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.get(url)
        data = resp.json()
        proc_specs = data["proc_specs"]

        assert len(proc_specs) == 1
        assert proc_specs[0]["services"] == [
            {"name": "web", "target_port": 8000, "port": 8000, "exposed_type": {"name": "bk/http"}, "protocol": "TCP"},
            {"name": "backend", "target_port": 8001, "port": 80, "exposed_type": None, "protocol": "TCP"},
        ]


class TestModuleProcessSpecWithMonitoringViewSet:
    @pytest.fixture()
    def _create_web_process_and_monitoring(self, bk_module):
        G(
            ModuleProcessSpec,
            module=bk_module,
            name="web",
            command=["python"],
            args=["-m", "http.server"],
            port=8000,
            services=[
                ProcService(name="web", target_port=8000, exposed_type={"name": "bk/http"}),
                ProcService(name="foo", target_port=8001, port=80),
            ],
        )
        G(
            ObservabilityConfig,
            module=bk_module,
            monitoring={"metrics": [{"service_name": "foo", "path": "/bar", "process": "web"}]},
        )

    @pytest.mark.parametrize(
        ("monitoring", "expected_status_code", "expected_detail_str"),
        [
            (None, 200, ""),
            ({"metric": {"service_name": "metric"}}, 200, ""),
            ({"metric": {"service_name": "foo"}}, 400, "not match any service"),
            ({"metric": {"service_name": "metric", "params": []}}, 400, "期望是包含类目的字典"),
        ],
    )
    def test_validate(
        self, api_client, bk_cnative_app, bk_module, monitoring, expected_status_code, expected_detail_str
    ):
        request_data = [
            {
                "name": "web",
                "image": "python:latest",
                "command": ["python", "-m"],
                "args": ["http.server"],
                "services": [
                    {"name": "web", "target_port": 5000, "port": 80, "exposed_type": {"name": "bk/http"}},
                    {"name": "metric", "target_port": 8001},
                ],
                "monitoring": monitoring,
            }
        ]

        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.post(url, data={"proc_specs": request_data})
        assert resp.status_code == expected_status_code
        assert expected_detail_str in resp.data.get("detail", "")

    def test_save(self, api_client, bk_cnative_app, bk_module):
        web_monitoring = {"metric": {"service_name": "metric", "path": "/metrics", "params": {"foo": "bar"}}}
        celery_monitoring = {"metric": {"service_name": "metric", "path": "/metrics", "params": {"foo": "bar"}}}
        request_data = [
            {
                "name": "web",
                "image": "python:latest",
                "command": ["python", "-m"],
                "args": ["http.server"],
                "services": [
                    {"name": "web", "target_port": 5000, "port": 80, "exposed_type": {"name": "bk/http"}},
                    {"name": "metric", "target_port": 5001},
                ],
                "monitoring": web_monitoring,
            },
            {
                "name": "celery",
                "image": "python:latest",
                "command": ["celery", "-l"],
                "args": ["info"],
                "services": [
                    {"name": "metric", "target_port": 8080},
                ],
                "monitoring": celery_monitoring,
            },
        ]

        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.post(url, data={"proc_specs": request_data})
        data = resp.json()

        proc_specs = data["proc_specs"]
        assert proc_specs[0]["monitoring"] == web_monitoring
        assert proc_specs[1]["monitoring"] == celery_monitoring
        assert ObservabilityConfig.objects.get(module=bk_module).monitoring.metrics == [
            Metric(**{"process": "web", **web_monitoring["metric"]}),  # type: ignore
            Metric(**{"process": "celery", **celery_monitoring["metric"]}),  # type: ignore
        ]

    @pytest.mark.usefixtures("_create_web_process_and_monitoring")
    def test_retrieve(self, api_client, bk_cnative_app, bk_module):
        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.get(url)
        data = resp.json()
        web_spec = data["proc_specs"][0]
        assert web_spec["monitoring"] == {"metric": {"service_name": "foo", "path": "/bar", "params": None}}


class TestModuleProcessSpecWithProcComponentsViewSet:
    @pytest.fixture(autouse=True)
    def _mock_components_dir(self, monkeypatch):
        test_dir = Path(settings.BASE_DIR) / "tests" / "support-files" / "test_components"
        monkeypatch.setattr("paasng.accessories.proc_components.manager.DEFAULT_COMPONENT_DIR", test_dir)

    @pytest.fixture()
    def web(self, bk_module):
        return G(
            ModuleProcessSpec,
            module=bk_module,
            name="web",
            command=["python"],
            args=["-m", "http.server"],
            port=8000,
            components=[
                Component(name="test_env_overlay", version="v2"),
            ],
        )

    @pytest.mark.parametrize(
        ("component_configs", "expected_status_code", "expected_detail_str"),
        [
            (None, 200, ""),
            (
                [
                    {
                        "name": "test_env_overlay",
                        "version": "v1",
                        "properties": {"env": [{"name": "proc_name", "value": "FOO"}, {"name": "key", "value": "1"}]},
                    }
                ],
                200,
                "",
            ),
            # invalid name or version
            (
                [
                    {
                        "name": "test_env_overlay",
                        "version": "v2",
                        "properties": {"env": [{"name": "proc_name", "value": "FOO"}, {"name": "key", "value": "1"}]},
                    }
                ],
                400,
                "proc_specs.0.components: 组件 test_env_overlay-v2 不存在",
            ),
            (
                [
                    {
                        "name": "not_exist",
                        "version": "v1",
                        "properties": {"env": [{"name": "proc_name", "value": "FOO"}, {"name": "key", "value": "1"}]},
                    }
                ],
                400,
                "proc_specs.0.components: 组件 not_exist-v1 不存在",
            ),
            # invalid properties
            (
                [
                    {
                        "name": "test_env_overlay",
                        "version": "v1",
                        "properties": {"invalid": [{"proc_xxx": "FOO", "value": "1"}]},
                    }
                ],
                400,
                "proc_specs.0.components: 参数校验失败",
            ),
        ],
    )
    def test_validate(
        self,
        api_client,
        bk_cnative_app,
        bk_module,
        component_configs,
        expected_status_code,
        expected_detail_str,
    ):
        request_data = [
            {
                "name": "web",
                "image": "python:latest",
                "command": ["python", "-m"],
                "args": ["http.server"],
                "components": component_configs,
            }
        ]

        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.post(url, data={"proc_specs": request_data})
        assert resp.status_code == expected_status_code
        assert expected_detail_str in resp.data.get("detail", "")

    def test_save(self, api_client, bk_cnative_app, bk_module):
        request_data = [
            {
                "name": "web",
                "image": "python:latest",
                "command": ["python", "-m"],
                "args": ["http.server"],
                "components": [
                    {
                        "name": "test_env_overlay",
                        "version": "v1",
                        "properties": {"env": [{"name": "proc_name", "value": "FOO"}, {"name": "key", "value": "1"}]},
                    }
                ],
            }
        ]

        url = f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/bkapp_model/process_specs/"
        resp = api_client.post(url, data={"proc_specs": request_data})
        assert resp.status_code == 200
        assert resp.data["proc_specs"][0]["components"] == [
            {
                "name": "test_env_overlay",
                "version": "v1",
                "properties": {"env": [{"name": "proc_name", "value": "FOO"}, {"name": "key", "value": "1"}]},
            }
        ]
