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
from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.processes.entities import (
    ExecAction as WLExecAction,
)
from paas_wl.bk_app.processes.entities import (
    HTTPGetAction as WLHTTPGetAction,
)
from paas_wl.bk_app.processes.entities import (
    Probe as WLProbe,
)
from paas_wl.bk_app.processes.entities import (
    ProbeSet as WLProbeSet,
)
from paas_wl.bk_app.processes.entities import TCPSocketAction as WLTCPSocketAction
from paas_wl.bk_app.processes.exceptions import InstanceNotFound
from paas_wl.bk_app.processes.kres_entities import Process
from paas_wl.bk_app.processes.kres_slzs import ProcessDeserializer, ProcessSerializer
from paas_wl.bk_app.processes.processes import (
    ProcessManager,
    gen_cnative_process_specs,
    list_cnative_module_processes_specs,
)
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.generation.v2 import V2Mapper
from paas_wl.infras.resources.kube_res.base import GVKConfig
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paasng.platform.bkapp_model.entities import (
    ExecAction,
    HTTPGetAction,
    Probe,
    ProbeSet,
    TCPSocketAction,
)
from paasng.platform.bkapp_model.models import ModuleProcessSpec
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
    @pytest.fixture
    def setup_log_pod(self, wl_app):
        """Setup the pod for log retrieving.

        测试需要兼容测试特殊执行环境(比如无 deployment controller 负责创建 Pod)，因此未采用
        创建进程 Process 而是使用直接创建 Pod 的方式。
        """
        k8s_client = get_client_by_app(wl_app)
        KPod(k8s_client).create_or_update(
            wl_app.scheduler_safe_name,
            namespace=wl_app.namespace,
            body=construct_foo_pod(wl_app.scheduler_safe_name, restart_policy="Never"),
        )

    @pytest.mark.parametrize(
        ("instance_name_suffix", "previous", "expected_exception"),
        [
            ("", False, None),  # 当前实例日志，正常情况
            ("", True, None),  # 上一次实例日志，正常情况
            ("-bad", False, InstanceNotFound),  # 不存在的当前实例
            ("-bad", True, InstanceNotFound),  # 不存在的上一次实例
        ],
    )
    def test_get_instance_logs(
        self, setup_log_pod, bk_stag_env, wl_app, instance_name_suffix, previous, expected_exception
    ):
        """测试获取实例日志，包含正常和异常情况"""
        instance_name = wl_app.scheduler_safe_name + instance_name_suffix

        if expected_exception:
            with pytest.raises(expected_exception):
                ProcessManager(bk_stag_env).get_instance_logs("", instance_name, previous, "main")
        else:
            logs = ProcessManager(bk_stag_env).get_instance_logs("", instance_name, previous, "main")
            assert logs is not None
            assert isinstance(logs, str)

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


class TestProcessAppEntity:
    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="v1.8.15",
            kind="Deployment",
            preferred_apiversion="apps/v1",
            available_apiversions=["apps/v1"],
        )

    @pytest.fixture()
    def process_data(self, wl_app):
        return {
            "metadata": {
                "labels": {
                    "pod_selector": "bkapp-utojeswq-stag-web",
                    "release_version": "5",
                    "region": "default",
                    "app_code": "utojeswq",
                    "module_name": "default",
                    "env": "stag",
                    "process_id": "web",
                    "category": "bkapp",
                    "mapper_version": "v2",
                    "bkapp.paas.bk.tencent.com/code": "utojeswq",
                    "bkapp.paas.bk.tencent.com/module-name": "default",
                    "bkapp.paas.bk.tencent.com/environment": "stag",
                    "bkapp.paas.bk.tencent.com/wl-app-name": "bkapp-utojeswq-stag",
                    "bkapp.paas.bk.tencent.com/resource-type": "process",
                },
                "name": "bkapp-utojeswq-stag--web",
                "annotations": {"bkapp.paas.bk.tencent.com/process-mapper-version": "v2"},
            },
            "spec": {
                "revisionHistoryLimit": 3,
                "strategy": {"type": "RollingUpdate", "rollingUpdate": {"maxUnavailable": 0, "maxSurge": "75%"}},
                "selector": {"matchLabels": {"pod_selector": "bkapp-utojeswq-stag-web"}},
                "minReadySeconds": 1,
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "env": [
                                    {"name": "SLUG_URL", "value": "bkpaas3-slug-packages/slug.tgz"},
                                    {
                                        "name": "SLUG_GET_URL",
                                        "value": "http://localhost:9090/bkpaas3-slug-packages/slug.tgz?AWSAccessKeyId=minio&Signature=5HZ4z4HNu2G%2FEZ9AwEsRoGXg%2F2I%3D&Expires=2371455749",
                                    },
                                ],
                                "lifecycle": {"pre_stop": {"_exec": {"command": ["sleep", "15"]}}},
                                "image": "bkpaas/slugrunner:latest",
                                "name": f"{wl_app.scheduler_safe_name_with_region}",
                                "command": ["bash", "/runner/init"],
                                "args": ["start", "web"],
                                "imagePullPolicy": "IfNotPresent",
                                "resources": {"limits": None, "requests": None},
                                "ports": [{"containerPort": 5000}],
                                "volumeMounts": [
                                    {
                                        "name": "applogs",
                                        "mountPath": "/app/logs",
                                        "readOnly": False,
                                    },
                                    {
                                        "name": "appv3logs",
                                        "mountPath": "/app/v3logs",
                                        "readOnly": False,
                                    },
                                ],
                                "readinessProbe": {
                                    "tcpSocket": {"port": 8080, "host": "127.0.0.1"},
                                    "initialDelaySeconds": 0,
                                    "timeoutSeconds": 1,
                                    "periodSeconds": 10,
                                    "successThreshold": 1,
                                    "failureThreshold": 3,
                                },
                                "livenessProbe": {
                                    "exec": {"command": ["/bin/healthz.sh"]},
                                    "initialDelaySeconds": 0,
                                    "timeoutSeconds": 1,
                                    "periodSeconds": 10,
                                    "successThreshold": 1,
                                    "failureThreshold": 3,
                                },
                                "startupProbe": {
                                    "httpGet": {
                                        "port": 80,
                                        "path": "/healthz",
                                        "httpHeaders": [],
                                    },
                                    "initialDelaySeconds": 0,
                                    "timeoutSeconds": 1,
                                    "periodSeconds": 10,
                                    "successThreshold": 1,
                                    "failureThreshold": 3,
                                },
                            }
                        ],
                        "volumes": [
                            {
                                "name": "applogs",
                                "hostPath": {
                                    "path": "/tmp/logs/default-bkapp-utojeswq-stag",
                                },
                            },
                            {
                                "name": "appv3logs",
                                "hostPath": {
                                    "path": "/tmp/v3logs/default-bkapp-utojeswq-stag/default",
                                },
                            },
                        ],
                        "imagePullSecrets": [{"name": "bkapp-utojeswq-stag--dockerconfigjson"}],
                        "automountServiceAccountToken": False,
                    },
                    "metadata": {
                        "labels": {
                            "pod_selector": "bkapp-utojeswq-stag-web",
                            "release_version": "5",
                            "region": "default",
                            "app_code": "utojeswq",
                            "module_name": "default",
                            "env": "stag",
                            "process_id": "web",
                            "category": "bkapp",
                            "mapper_version": "v2",
                            "bkapp.paas.bk.tencent.com/code": "utojeswq",
                            "bkapp.paas.bk.tencent.com/module-name": "default",
                            "bkapp.paas.bk.tencent.com/environment": "stag",
                            "bkapp.paas.bk.tencent.com/wl-app-name": "bkapp-utojeswq-stag",
                            "bkapp.paas.bk.tencent.com/resource-type": "process",
                        },
                        "name": "bkapp-utojeswq-stag--web",
                    },
                },
                "replicas": 0,
            },
            "status": {},
            "apiVersion": "apps/v1",
            "kind": "Deployment",
        }

    @pytest.fixture()
    def module_process_spec(self, bk_stag_env, wl_app, wl_release):
        return ModuleProcessSpec.objects.create(
            module=bk_stag_env.module,
            name="web",
            probes=ProbeSet(
                liveness=Probe(exec=ExecAction(command=["/bin/healthz.sh"])),
                readiness=Probe(tcp_socket=TCPSocketAction(port=8080, host="127.0.0.1")),
                startup=Probe(http_get=HTTPGetAction(port=80, path="/healthz")),
            ),
        )

    def test_from_release_with_probes(self, wl_app, wl_release, module_process_spec):
        process = Process.from_release(type_="web", release=wl_release)
        assert process.probes.liveness.exec.command == ["/bin/healthz.sh"]  # type: ignore
        assert process.probes.readiness.tcp_socket.port == 8080  # type: ignore
        assert process.probes.readiness.tcp_socket.host == "127.0.0.1"  # type: ignore
        assert process.probes.startup.http_get.port == 80  # type: ignore
        assert process.probes.startup.http_get.path == "/healthz"  # type: ignore

    def test_process_deserializer_with_probes(self, wl_app, wl_release, module_process_spec, gvk_config):
        process = Process.from_release(type_="web", release=wl_release)
        data = ProcessSerializer(Process, gvk_config).serialize(process, None, mapper_version=V2Mapper)
        data["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = {
            "tcpSocket": {"port": 8080, "host": "127.0.0.1"},
            "initialDelaySeconds": 0,
            "timeoutSeconds": 1,
            "periodSeconds": 10,
            "successThreshold": 1,
            "failureThreshold": 3,
        }
        data["spec"]["template"]["spec"]["containers"][0]["startupProbe"] = {
            "httpGet": {
                "port": 80,
                "path": "/healthz",
                "httpHeaders": [],
            },
            "initialDelaySeconds": 0,
            "timeoutSeconds": 1,
            "periodSeconds": 10,
            "successThreshold": 1,
            "failureThreshold": 3,
        }
        data["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = {
            "exec": {"command": ["/bin/healthz.sh"]},
            "initialDelaySeconds": 0,
            "timeoutSeconds": 1,
            "periodSeconds": 10,
            "successThreshold": 1,
            "failureThreshold": 3,
        }

    def test_process_serializer_with_probes(self, wl_app, gvk_config, process_data):
        kube_data = ResourceInstance(None, process_data)
        ProcessDeserializer(Process, gvk_config).deserialize(wl_app, kube_data).probes = WLProbeSet(
            liveness=WLProbe(exec=WLExecAction(command=["/bin/healthz.sh"])),
            readiness=WLProbe(tcp_socket=WLTCPSocketAction(port=8080, host="127.0.0.1")),
            startup=WLProbe(http_get=WLHTTPGetAction(port=80, path="/healthz")),
        )
