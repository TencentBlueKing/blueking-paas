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

from paas_wl.bk_app.deploy.app_res.controllers import BuildHandler
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
from paas_wl.workloads.release_controller.entities import ContainerRuntimeSpec
from paasng.platform.engine.configurations.building import SlugBuilderTemplate
from paasng.platform.engine.deploy.bg_build.utils import generate_builder_name

from .conftest import construct_foo_pod

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

DummyObjectList = namedtuple("DummyObjectList", "items metadata")

# Make a shortcut name
RG = settings.DEFAULT_REGION_NAME


@pytest.fixture()
def build_handler(wl_app) -> BuildHandler:
    return BuildHandler.new_by_app(wl_app)


class TestBuildHandler:
    @pytest.fixture()
    def pod_template(self):
        return SlugBuilderTemplate(
            name="slug-builder",
            namespace="bkapp-foo-stag",
            runtime=ContainerRuntimeSpec(image="blueking-fake.com:8090/bkpaas/slugrunner:latest", envs={"test": "1"}),
            schedule=Schedule(
                cluster_name="",
                node_selector={},
                tolerations=[{"key": "region", "operator": "Equal", "effect": "NoExecute", "value": "sh"}],
            ),
        )

    def test_build_slug(self, build_handler, pod_template):
        namespace_create = Mock(return_value=None)
        namespace_check = Mock(return_value=True)

        pod_body = parse_pod(ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Completed"}}))
        kpod_get = Mock(return_value=pod_body)

        create_pod_body = parse_pod(
            ResourceInstance(None, {"kind": "Pod", "metadata": {"name": "bkapp-foo-stag-slug-pod"}})
        )
        kpod_create_or_update = Mock(return_value=(create_pod_body, True))

        with patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get_or_create", namespace_create), patch(
            "paas_wl.infras.resources.base.kres.KNamespace.wait_for_default_sa", namespace_check
        ), patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get), patch(
            "paas_wl.infras.resources.base.kres.NameBasedOperations.create_or_update", kpod_create_or_update
        ), patch("paas_wl.bk_app.deploy.app_res.controllers.WaitPodDelete.wait"):
            build_handler.build_slug(template=pod_template)
            assert kpod_get.called
            assert kpod_create_or_update.called

            args, kwargs = kpod_create_or_update.call_args_list[0]
            body = kwargs.get("body")
            assert body["metadata"]["name"] == "slug-builder"
            assert body["spec"]["containers"][0]["env"][0]["value"] == "1"
            assert len(body["spec"]["tolerations"]) == 1
            assert body["spec"]["tolerations"][0]["key"] == "region"
            assert body["spec"]["tolerations"][0]["operator"] == "Equal"

    def test_build_slug_exist(self, build_handler, pod_template):
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

        with patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get_or_create", namespace_create), patch(  # noqa: SIM117
            "paas_wl.infras.resources.base.kres.KNamespace.wait_for_default_sa", namespace_check
        ), patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get):
            with pytest.raises(ResourceDuplicate):
                build_handler.build_slug(template=pod_template)

    def test_delete_builder_pod(self, build_handler):
        pod_body = ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Completed"}})
        kpod_get = Mock(return_value=pod_body)
        kpod_delete = Mock(return_value=None)

        with patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get), patch(
            "paas_wl.infras.resources.base.kres.NameBasedOperations.delete", kpod_delete
        ):
            build_handler.delete_builder(namespace="bkapp-foo-stag", name="slug-builder")

            assert kpod_get.called
            assert kpod_delete.called
            args, kwargs = kpod_delete.call_args_list[0]
            assert args[0] == "slug-builder"
            assert kwargs.get("namespace") == "bkapp-foo-stag"

    def test_delete_builder_pod_missing(self, build_handler):
        kpod_get = Mock(side_effect=ResourceMissing("bkapp-foo-stag-slug-pod", "bkapp-foo-stag"))
        kpod_delete = Mock(return_value=None)

        with patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get), patch(
            "paas_wl.infras.resources.base.kres.NameBasedOperations.delete", kpod_delete
        ):
            build_handler.delete_builder(namespace="bkapp-foo-stag", name="bkapp-foo-stag")

            assert kpod_get.called
            assert not kpod_delete.called

    def test_delete_builder_pod_running(self, build_handler):
        pod_body = ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Running"}})
        kpod_get = Mock(return_value=pod_body)
        kpod_delete = Mock(return_value=None)

        with patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get), patch(
            "paas_wl.infras.resources.base.kres.NameBasedOperations.delete", kpod_delete
        ):
            build_handler.delete_builder(namespace="bkapp-foo-stag", name="bkapp-foo-stag")

            assert kpod_get.called
            assert not kpod_delete.called


@pytest.mark.auto_create_ns()
class TestBuildHandlerWithNS:
    """New test cases using pytest"""

    def test_interrupt_builder(self, wl_app, k8s_client, build_handler):
        builder_pod_name = BuildHandler.normalize_builder_name(generate_builder_name(wl_app))
        KPod(k8s_client).create_or_update(
            builder_pod_name, namespace=wl_app.namespace, body=construct_foo_pod(builder_pod_name)
        )

        assert (
            build_handler.interrupt_builder(
                namespace=wl_app.namespace,
                name=generate_builder_name(wl_app),
            )
            is True
        )

    def test_interrupt_builder_non_existent(self, wl_app, build_handler):
        assert (
            build_handler.interrupt_builder(
                namespace=wl_app.namespace,
                name=generate_builder_name(wl_app),
            )
            is False
        )

    def test_wait_for_succeeded_no_pod(self, wl_app, build_handler):
        with pytest.raises(PodAbsentError):
            build_handler.wait_for_succeeded(wl_app.namespace, generate_builder_name(wl_app), timeout=1)

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
    def test_wait_for_succeeded(self, phase, exc_context, wl_app, build_handler, k8s_client):
        pod_name = BuildHandler.normalize_builder_name(generate_builder_name(wl_app))
        body = construct_foo_pod(pod_name, restart_policy="Never")

        KPod(k8s_client).create_or_update(pod_name, namespace=wl_app.namespace, body=body)

        body = {"status": {"phase": phase, "conditions": []}}
        KPod(k8s_client).patch_subres("status", pod_name, namespace=wl_app.namespace, body=body, ptype=PatchType.MERGE)

        with exc_context:
            build_handler.wait_for_succeeded(wl_app.namespace, pod_name, timeout=1)
