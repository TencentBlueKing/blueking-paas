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

from unittest import mock

import pytest

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.processes.processes import (
    ProcessManager,
    gen_cnative_process_specs,
    list_cnative_module_processes_specs,
)
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.utils.basic import get_client_by_app
from tests.paas_wl.infras.resources.base.test_kres import construct_foo_pod

pytestmark = [pytest.mark.django_db(databases=["default", "workloads"]), pytest.mark.auto_create_ns]


def testlist_gen_cnative_process_specs():
    specs = gen_cnative_process_specs(
        BkAppResource(
            metadata={"name": "test"},
            spec={
                "processes": [
                    {"name": "web", "resQuotaPlan": "4C2G"},
                    {
                        "name": "worker",
                        "resQuotaPlan": "default",
                        "autoscaling": {"minReplicas": 1, "maxReplicas": 3, "policy": "default"},
                    },
                ],
                "envOverlay": {
                    "replicas": [{"process": "worker", "count": 0, "envName": "stag"}],
                    "autoscaling": [
                        {
                            "process": "worker",
                            "minReplicas": 3,
                            "maxReplicas": 5,
                            "envName": "stag",
                            "policy": "default",
                        }
                    ],
                },
            },
        ),
        "stag",
    )

    assert specs[0].name == "web"
    assert specs[0].plan_name == "4C2G"
    assert specs[0].target_replicas == 1
    assert specs[0].autoscaling is False
    assert specs[0].scaling_config is None
    assert specs[0].resource_limit == {"cpu": "4000m", "memory": "2048Mi"}
    assert specs[0].resource_limit_quota == {"cpu": 4000, "memory": 2048}
    assert specs[0].resource_requests == {"cpu": "200m", "memory": "1024Mi"}
    assert specs[0].target_status == "start"

    assert specs[1].name == "worker"
    assert specs[1].plan_name == "default"
    assert specs[1].target_replicas == 0
    assert specs[1].autoscaling is True
    assert specs[1].scaling_config["min_replicas"] == 3  # type: ignore
    assert specs[1].scaling_config["max_replicas"] == 5  # type: ignore
    assert specs[1].resource_limit == {"cpu": "4000m", "memory": "1024Mi"}
    assert specs[1].resource_limit_quota == {"cpu": 4000, "memory": 1024}
    assert specs[1].resource_requests == {"cpu": "200m", "memory": "256Mi"}
    assert specs[1].target_status == "stop"


@pytest.mark.usefixtures("bk_stag_wl_app")
def test_list_cnative_module_processes_specs(bk_cnative_app):
    with mock.patch(
        "paas_wl.bk_app.processes.processes.list_mres_by_env",
        return_value=[
            BkAppResource(
                metadata={
                    "name": f"{bk_cnative_app.code}",
                    "annotations": {"bkapp.paas.bk.tencent.com/module-name": "default"},
                },
                spec={"processes": [{"name": "web", "replicas": 1, "resQuotaPlan": "4C4G"}]},
            ),
            BkAppResource(
                metadata={
                    "name": f"{bk_cnative_app.code}-m-foo",
                    "annotations": {"bkapp.paas.bk.tencent.com/module-name": "foo"},
                },
                spec={"processes": [{"name": "web", "replicas": 2}]},
            ),
        ],
    ):
        specs = list_cnative_module_processes_specs(bk_cnative_app, "stag")
        assert specs["default"] == [
            {
                "name": "web",
                "max_replicas": 10,
                "target_replicas": 1,
                "plan_name": "4C4G",
                "autoscaling": False,
                "scaling_config": None,
                "target_status": "start",
                "resource_limit": {"cpu": "4000m", "memory": "4096Mi"},
                "resource_limit_quota": {"cpu": 4000, "memory": 4096},
                "resource_requests": {"cpu": "200m", "memory": "2048Mi"},
            }
        ]

        assert specs["foo"] == [
            {
                "name": "web",
                "target_replicas": 2,
                "target_status": "start",
                "max_replicas": 10,
                "plan_name": "default",
                "autoscaling": False,
                "scaling_config": None,
                "resource_limit": {"cpu": "4000m", "memory": "1024Mi"},
                "resource_limit_quota": {"cpu": 4000, "memory": 1024},
                "resource_requests": {"cpu": "200m", "memory": "256Mi"},
            }
        ]


class TestProcessManager:
    def test_get_previous_logs(self, bk_stag_env, wl_app):
        """
        测试获取进程实例上一次运行时重启日志

        测试需要兼容测试流水线的执行环境(无 controller)，因此通过下发 pod 进行日志测试
        原设计是通过创建 process，再获取 pod 日志
        """
        k8s_client = get_client_by_app(wl_app)
        KPod(k8s_client).create_or_update(
            wl_app.scheduler_safe_name,
            namespace=wl_app.namespace,
            body=construct_foo_pod(wl_app.scheduler_safe_name, restart_policy="Never"),
        )

        manager = ProcessManager(bk_stag_env)
        logs = manager.get_previous_logs("", wl_app.scheduler_safe_name, "main")
        assert logs is not None

    @pytest.mark.usefixtures("bk_stag_wl_app")
    def test_list_cnative_processes_specs(self, bk_cnative_app, bk_stag_env):
        with mock.patch(
            "paas_wl.bk_app.processes.processes.get_mres_from_cluster",
            return_value=BkAppResource(metadata={"name": bk_cnative_app.code}, spec={"processes": [{"name": "foo"}]}),
        ):
            specs = ProcessManager(bk_stag_env).list_processes_specs()
            assert specs[0] == {
                "name": "foo",
                "max_replicas": 10,
                "target_replicas": 1,
                "plan_name": "default",
                "autoscaling": False,
                "scaling_config": None,
                "target_status": "start",
                "resource_limit": {"cpu": "4000m", "memory": "1024Mi"},
                "resource_limit_quota": {"cpu": 4000, "memory": 1024},
                "resource_requests": {"cpu": "200m", "memory": "256Mi"},
            }
