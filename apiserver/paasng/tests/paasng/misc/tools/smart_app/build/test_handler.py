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

from collections import namedtuple
from unittest.mock import Mock, patch

import pytest
from blue_krill.contextlib import nullcontext as does_not_raise
from django.conf import settings
from django.utils import timezone
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import (
    PodAbsentError,
    PodNotSucceededError,
    PodTimeoutError,
    ResourceDuplicate,
    ResourceMissing,
)
from paas_wl.infras.resources.base.kres import KPod, PatchType
from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.utils.kubestatus import parse_pod
from paasng.misc.tools.smart_app.build.handler import ContainerRuntimeSpec, SmartBuilderTemplate, SmartBuildHandler
from tests.paas_wl.bk_app.deploy.app_res.conftest import construct_foo_pod
from tests.utils.cluster import build_default_cluster

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

DummyObjectList = namedtuple("DummyObjectList", "items metadata")

# Make a shortcut name
RG = settings.DEFAULT_REGION_NAME

# 获取默认测试集群
cluster, _ = build_default_cluster()


@pytest.fixture()
def smart_build_handler() -> SmartBuildHandler:
    return SmartBuildHandler(get_client_by_cluster_name(cluster.name))


class TestSmartBuildHandler:
    @pytest.fixture()
    def pod_template(self):
        return SmartBuilderTemplate(
            name="test_builder",
            namespace="smart-app-builder",
            runtime=ContainerRuntimeSpec(
                image="blueking-fake.com/bkpaas/smart-builder:latest",
                envs={"test": "bar"},
            ),
            schedule=Schedule(
                cluster_name=cluster.name,
                node_selector={},
                tolerations=[],
            ),
        )

    def test_build_pod(self, smart_build_handler, pod_template):
        namespace_create = Mock(return_value=None)
        namespace_check = Mock(return_value=True)

        pod_body = parse_pod(ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Completed"}}))
        kpod_get = Mock(return_value=pod_body)

        create_pod_body = parse_pod(ResourceInstance(None, {"kind": "Pod", "metadata": {"name": "smart-builder-pod"}}))
        kpod_create_or_update = Mock(return_value=(create_pod_body, True))

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get_or_create", namespace_create),
            patch("paas_wl.infras.resources.base.kres.KNamespace.wait_for_default_sa", namespace_check),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.create_or_update", kpod_create_or_update),
            patch("paas_wl.bk_app.deploy.app_res.controllers.WaitPodDelete.wait"),
        ):
            smart_build_handler.build_pod(pod_template)
            assert kpod_get.called
            assert kpod_create_or_update.called

            args, kwargs = kpod_create_or_update.call_args_list[0]
            body = kwargs.get("body")
            assert body["metadata"]["name"] == "smart-builder"
            assert body["spec"]["containers"][0]["env"][0]["value"] == "bar"

    def test_build_pod_exist(self, smart_build_handler, pod_template):
        namespace_create = Mock(return_value=None)
        namespace_check = Mock(return_value=True)

        pod_body = ResourceInstance(
            None,
            {
                "kind": "Pod",
                "metadata": {"name": "foo"},
                "status": {"phase": "Running", "startTime": timezone.now().isoformat()},
            },
        )
        kpod_get = Mock(return_value=pod_body)

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get_or_create", namespace_create),
            patch("paas_wl.infras.resources.base.kres.KNamespace.wait_for_default_sa", namespace_check),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get),
            pytest.raises(ResourceDuplicate),
        ):
            smart_build_handler.build_pod(pod_template)

    def test_delete_builder_pod(self, smart_build_handler):
        pod_body = ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Completed"}})
        kpod_get = Mock(return_value=pod_body)
        kpod_delete = Mock(return_value=None)

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.delete", kpod_delete),
        ):
            smart_build_handler.delete_builder(namespace="bkapp-foo-stag", name="test_builder")

            assert kpod_get.called
            assert kpod_delete.called
            args, kwargs = kpod_delete.call_args_list[0]
            assert args[0] == "smart-builder"
            assert kwargs.get("namespace") == "smart-app-builder"

    def test_delete_builder_pod_missing(self, smart_build_handler):
        kpod_get = Mock(side_effect=ResourceMissing("bkapp-foo-stag-slug-pod", "bkapp-foo-stag"))
        kpod_delete = Mock(return_value=None)

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.delete", kpod_delete),
        ):
            smart_build_handler.delete_builder(namespace="bkapp-foo-stag", name="bkapp-foo-stag")

            assert kpod_get.called
            assert not kpod_delete.called

    def test_delete_builder_pod_running(self, smart_build_handler):
        pod_body = ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Running"}})
        kpod_get = Mock(return_value=pod_body)
        kpod_delete = Mock(return_value=None)

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.delete", kpod_delete),
        ):
            smart_build_handler.delete_builder(namespace="bkapp-foo-stag", name="bkapp-foo-stag")

            assert kpod_get.called
            assert not kpod_delete.called


@pytest.mark.auto_create_ns
class TestSmartBuilderHandlerWithNS:
    """New test case using pytest"""

    def test_wait_for_succeeded_no_pod(self, smart_build_handler):
        with pytest.raises(PodAbsentError):
            smart_build_handler.wait_for_succeeded("smart-app-builder", "dummy-pod-name", timeout=1)

    @pytest.mark.parametrize(
        ("phase", "exc_context"),
        [
            ("Pending", pytest.raises(PodTimeoutError)),
            ("Running", pytest.raises(PodTimeoutError)),
            ("Failed", pytest.raises(PodNotSucceededError)),
            ("Unknown", pytest.raises(PodNotSucceededError)),
            ("Succeeded", does_not_raise()),
        ],
    )
    def test_wait_for_succeeded(self, phase, exc_context, smart_build_handler, k8s_client):
        pod_name = smart_build_handler.normalize_builder_name("test_builder")
        body = construct_foo_pod(pod_name, restart_policy="Never")

        KPod(k8s_client).create_or_update(pod_name, namespace="smart-app-builder", body=body)

        body = {"status": {"phase": phase, "conditions": []}}
        KPod(k8s_client).patch_subres(
            "status", pod_name, namespace="smart-app-builder", body=body, ptype=PatchType.MERGE
        )

        with exc_context:
            smart_build_handler.wait_for_succeeded("smart-app-builder", pod_name, timeout=1)
