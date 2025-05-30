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

from types import SimpleNamespace
from unittest import mock

import pytest
from django.conf import settings

from paas_wl.bk_app.processes.kres_entities import Process
from paas_wl.bk_app.processes.kres_slzs import extract_type_from_name
from paas_wl.bk_app.processes.readers import instance_kmodel, process_kmodel
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.generation.version import get_mapper_version
from paas_wl.infras.resources.kube_res.base import AppEntityManager
from paas_wl.infras.resources.utils.basic import get_client_by_app
from tests.paas_wl.infras.resources.base.test_kres import ResourceInstance
from tests.paas_wl.utils.basic import make_container_status
from tests.paas_wl.utils.wl_app import create_wl_release

pytestmark = [pytest.mark.django_db(databases=["default", "workloads"]), pytest.mark.auto_create_ns]


@pytest.fixture()
def client(wl_app):
    return get_client_by_app(wl_app)


@pytest.fixture()
def release(wl_app, set_structure):
    set_structure(wl_app, {"web": 2})
    return create_wl_release(
        wl_app=wl_app,
        release_params={
            "version": 2,
            "procfile": {"web": "gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile"},
        },
    )


@pytest.fixture()
def process(release):
    return Process.from_release(type_="web", release=release)


@pytest.fixture()
def process_manager():
    return AppEntityManager(Process)


@pytest.fixture()
def v2_mapper(process):
    return get_mapper_version(target="v2")


@pytest.fixture()
def pod_body(wl_app, process_manager, process, v2_mapper):
    """Create a instance pod body."""
    pod_name = v2_mapper.proc_resources(process=process).pod_name
    serializer = process_manager._make_serializer(wl_app)
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"labels": v2_mapper.proc_resources(process=process).labels, "name": pod_name},
        "spec": serializer._construct_pod_body_specs(process),  # type: ignore
    }


class TestProcInstManager:
    """Test cases for ProcInst"""

    @pytest.fixture()
    def pod(self, client, process, pod_body):
        pod, _ = KPod(client).create_or_update(
            name=pod_body["metadata"]["name"], namespace=process.app.namespace, body=pod_body
        )
        return pod

    def test_query_instances(self, wl_app, pod):
        # Query process instances
        insts = instance_kmodel.list_by_process_type(wl_app, "web")
        assert len(insts) == 1
        assert insts[0].process_type == "web"
        assert insts[0].state == "Pending"
        assert insts[0].rich_status == "Pending"
        assert insts[0].envs

    def test_query_instances_without_process_id_label(self, client, wl_app, pod):
        # Delete `process_id` label to simulate resources created by legacy engine versions
        labels = dict(pod.metadata.labels)
        del labels["process_id"]
        KPod(client).patch(
            name=pod.metadata.name, body={"metadata": {"labels": labels}}, namespace=pod.metadata.namespace
        )

        # Query process instances
        insts = instance_kmodel.list_by_process_type(wl_app, "web")
        assert len(insts) == 1

    def test_watch_from_rv0(self, client, wl_app, pod):
        labels = dict(pod.metadata.labels)
        # Update labels to produce events
        labels["foo"] = "bar"
        KPod(client).patch(
            name=pod.metadata.name, body={"metadata": {"labels": labels}}, namespace=pod.metadata.namespace
        )

        events = list(instance_kmodel.watch_by_app(wl_app, resource_version=0, timeout_seconds=1))
        assert len(events) > 0

    def test_watch_from_empty_rv(self, wl_app, pod):
        inst = instance_kmodel.list_by_process_type(wl_app, "web")[0]
        events = list(
            instance_kmodel.watch_by_app(wl_app, resource_version=inst.get_resource_version(), timeout_seconds=1)
        )
        assert len(events) == 0

        events = list(instance_kmodel.watch_by_app(wl_app, resource_version=0, timeout_seconds=1))
        assert len(events) > 0

    def test_watch_unknown_res(self, wl_app, client, process_manager, process, v2_mapper):
        pod_name = v2_mapper.proc_resources(process=process).pod_name
        serializer = process_manager._make_serializer(wl_app)
        pod_body = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"labels": {}, "name": pod_name},
            "spec": serializer._construct_pod_body_specs(process),  # type: ignore
        }
        pod, _ = KPod(client).create_or_update(name=pod_name, namespace=process.app.namespace, body=pod_body)
        events = list(instance_kmodel.watch_by_app(wl_app, resource_version=0, timeout_seconds=1))
        assert len(events) > 0
        event = None
        for event in events:
            if event.type == "ERROR":
                break
        assert event is not None
        assert event.error_message == "No process_type found in resource"

    def test_get_logs(self, wl_app, pod):
        # Query process instances
        inst = instance_kmodel.list_by_process_type(wl_app, "web")[0]
        with mock.patch("paas_wl.bk_app.processes.kres_entities.Instance.Meta.kres_class") as kp:
            instance_kmodel.get_logs(inst)
            assert kp().get_log.called

    def test_list_by_app_with_meta(self, wl_app, pod):
        resources = instance_kmodel.list_by_app_with_meta(wl_app)

        assert resources.metadata is not None
        rv = resources.get_resource_version()
        assert isinstance(rv, str)
        assert rv != ""


class TestProcInstManagerTerminated:
    """Test listing terminated instances, the case uses mock data because terminating
    a pod in test environment using real kubernetes cluster produces unstable result.
    """

    def test_list(self, wl_app, pod_body):
        # Make a terminated pod body
        pod_body["status"] = {
            "phase": "Failed",
            "containerStatuses": [
                make_container_status(
                    state={"terminated": {"reason": "Terminated", "exitCode": 1}},
                    last_state={"terminated": {"reason": "test exit", "exitCode": 137}},
                )
            ],
        }

        # Using mock to simulate terminated pod
        pods = SimpleNamespace(metadata=None, items=[ResourceInstance(None, pod_body)])
        with mock.patch("paas_wl.infras.resources.base.kres.BatchOperations.list", return_value=pods):
            inst = instance_kmodel.list_by_process_type(wl_app, "web")[0]

        assert inst.state == "Failed"
        assert inst.rich_status == "Terminated"
        assert inst.terminated_info["exit_code"] == 137
        assert inst.terminated_info["reason"] == "test exit"


class TestProcSpecsManager:
    """Test cases for ProcSpecs"""

    @pytest.fixture()
    def process(self, wl_app, release, process_manager, process, v2_mapper):
        process_manager.create(process, mapper_version=v2_mapper)
        return process

    def test_query_instances(self, process):
        # Query ProcSpecs objects
        objs = process_kmodel.list_by_app(process.app)
        assert len(objs) == 1
        assert objs[0].type == "web"
        assert objs[0].replicas == 2

        obj = process_kmodel.get_by_type(process.app, "web")
        # 集成测试中的 k8s 集群会修改 metadata
        obj.metadata = {}
        objs[0].metadata = {}
        assert obj == objs[0]

    def test_watch_from_rv0(self, process):
        events = list(process_kmodel.watch_by_app(process.app, resource_version=0, timeout_seconds=1))
        assert len(events) > 0
        event = events[0]
        assert event.type == "ADDED"
        assert event.res_object is not None
        assert event.res_object.type == "web"


class TestExtractTypeFromName:
    @pytest.mark.parametrize(
        ("name", "namespace", "proc_type"),
        [
            (
                f"{settings.DEFAULT_REGION_NAME}-bkapp-foo-prod-web-gunicorn-deployment",
                "bkapp-foo-prod",
                "web",
            ),
            (
                f"{settings.DEFAULT_REGION_NAME}-bkapp-foo-prod-web-gunicorn-deployment-858bf9c468-rms24",
                "bkapp-foo-prod",
                "web",
            ),
            ("invalid_name", "xxx", None),
        ],
    )
    def test_main(self, name, namespace, proc_type):
        assert extract_type_from_name(name, namespace) == proc_type
