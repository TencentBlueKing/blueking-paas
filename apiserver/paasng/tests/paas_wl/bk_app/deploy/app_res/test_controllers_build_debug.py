# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from unittest.mock import Mock, patch

import arrow
import pytest
from django.utils import timezone
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.bk_app.deploy.app_res.controllers import BuildHandler, BuildProbePoller, BuildProbeStatus
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.utils.kubestatus import parse_pod
from paas_wl.workloads.release_controller.entities import ContainerRuntimeSpec
from paasng.platform.engine.configurations.building import SlugBuilderTemplate
from paasng.platform.engine.deploy.bg_build.utils import generate_builder_name

from .conftest import construct_foo_pod

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def build_handler(wl_app) -> BuildHandler:
    return BuildHandler.new_by_app(wl_app)


class TestBuildProbePoller:
    """Tests for BuildProbePoller polling logic."""

    def _make_probe_poller(self, build_handler, namespace="ns-foo", name="builder-1"):
        return BuildProbePoller(build_handler, namespace, name)

    @patch("time.sleep", return_value=None)
    @pytest.mark.parametrize(
        ("retry_return", "expected"),
        [
            (BuildProbeStatus.SUCCEEDED, BuildProbeStatus.SUCCEEDED),
            (BuildProbeStatus.FAILED, BuildProbeStatus.FAILED),
        ],
    )
    def test_poll_failed_with_retry(self, mock_sleep, build_handler, retry_return, expected):
        """FAILED 后重检一次以消除时序误判, 重检结果决定最终返回值."""
        build_handler.check_probe_and_pod = Mock(side_effect=[BuildProbeStatus.FAILED, retry_return])

        poller = self._make_probe_poller(build_handler)
        result = poller.poll_until_ready()
        assert result == expected
        assert build_handler.check_probe_and_pod.call_count == 2

    @patch("time.sleep", return_value=None)
    @patch("time.monotonic", side_effect=[0, 100, 200, 100000])  # 超时
    def test_poll_timeout(self, mock_sleep, mock_monotonic, build_handler):
        """超过 BUILD_PROCESS_TIMEOUT 后返回 None."""
        build_handler.check_probe_and_pod = Mock(return_value=BuildProbeStatus.BUILDING)

        poller = self._make_probe_poller(build_handler)
        result = poller.poll_until_ready()
        assert result is None


@pytest.mark.auto_create_ns
class TestCheckProbeAndPod:
    """Tests for BuildHandler.check_probe_and_pod method."""

    @pytest.mark.parametrize("phase", ["Succeeded", "Failed"])
    def test_pod_terminal_phase_returns_pod_ended(self, build_handler, k8s_client, wl_app, phase):
        """Pod 处于终止阶段 (Succeeded/Failed) 应返回 POD_ENDED."""
        pod_name = generate_builder_name(wl_app)
        body = construct_foo_pod(pod_name, restart_policy="Never")
        KPod(k8s_client).create_or_update(pod_name, namespace=wl_app.namespace, body=body)
        KPod(k8s_client).patch_subres(
            "status",
            pod_name,
            namespace=wl_app.namespace,
            body={"status": {"phase": phase, "conditions": []}},
            ptype="merge",
        )

        result = build_handler.check_probe_and_pod(wl_app.namespace, pod_name)
        assert result == BuildProbeStatus.POD_ENDED

    @pytest.mark.parametrize(
        "container_statuses",
        [
            [],
            [{"name": "pod", "started": False, "ready": False}],
        ],
    )
    def test_pod_running_returns_building(self, build_handler, k8s_client, wl_app, container_statuses):
        """Pod Running 但容器未就绪时应返回 BUILDING."""
        pod_name = generate_builder_name(wl_app)
        body = construct_foo_pod(pod_name, restart_policy="Never")
        KPod(k8s_client).create_or_update(pod_name, namespace=wl_app.namespace, body=body)
        KPod(k8s_client).patch_subres(
            "status",
            pod_name,
            namespace=wl_app.namespace,
            body={"status": {"phase": "Running", "conditions": [], "containerStatuses": container_statuses}},
            ptype="merge",
        )

        result = build_handler.check_probe_and_pod(wl_app.namespace, pod_name)
        assert result == BuildProbeStatus.BUILDING

    @pytest.mark.parametrize(
        ("ready", "expected"),
        [
            (True, BuildProbeStatus.SUCCEEDED),
            (False, BuildProbeStatus.FAILED),
        ],
    )
    def test_pod_running_started(self, build_handler, k8s_client, wl_app, ready, expected):
        """容器已启动时, ready 决定 SUCCEEDED 或 FAILED (构建失败保活)."""
        pod_name = generate_builder_name(wl_app)
        body = construct_foo_pod(pod_name, restart_policy="Never")
        KPod(k8s_client).create_or_update(pod_name, namespace=wl_app.namespace, body=body)
        KPod(k8s_client).patch_subres(
            "status",
            pod_name,
            namespace=wl_app.namespace,
            body={
                "status": {
                    "phase": "Running",
                    "conditions": [],
                    "containerStatuses": [{"name": pod_name, "started": True, "ready": ready}],
                }
            },
            ptype="merge",
        )

        result = build_handler.check_probe_and_pod(wl_app.namespace, pod_name)
        assert result == expected

    def test_pod_resource_missing(self, build_handler, wl_app):
        """Pod 不存在时抛出 ResourceMissing."""
        with pytest.raises(ResourceMissing):
            build_handler.check_probe_and_pod(wl_app.namespace, "non-existent-pod")


class TestBuildFinishedAt:
    """Tests for is_debug_window_available method."""

    @pytest.mark.parametrize(
        ("annotations", "expected"),
        [
            ({}, True),
            ({"build_finished_at": arrow.now().shift(seconds=-60).isoformat()}, True),
            ({"build_finished_at": arrow.now().shift(seconds=-3600).isoformat()}, False),
            ({"build_finished_at": "invalid-date"}, True),
            (None, True),
        ],
    )
    def test_is_debug_window_available(self, annotations, expected):
        """基于 build_finished_at 注解判断调试窗口是否可用."""
        pod = Mock()
        pod.metadata.annotations = annotations
        assert BuildHandler.is_debug_window_available(pod, 1800) is expected


class TestBuildSlugWithDebug:
    """Tests for BuildHandler.build_slug with build_debug flag."""

    @staticmethod
    def _make_template(wl_app, build_debug: bool) -> SlugBuilderTemplate:
        return SlugBuilderTemplate(
            name="slug-builder",
            namespace=wl_app.namespace,
            runtime=ContainerRuntimeSpec(
                image="blueking-fake.com:8090/bkpaas/slugrunner:latest",
                envs={"test": "1"},
            ),
            schedule=Schedule(
                cluster_name="",
                node_selector={},
                tolerations=[],
            ),
            build_debug=build_debug,
        )

    @pytest.mark.parametrize("build_debug", [True, False])
    def test_build_slug_probes_based_on_debug(self, build_handler, wl_app, build_debug):
        """build_debug 决定是否在 Pod spec 中注入探针和 label."""
        pod_template = self._make_template(wl_app, build_debug)
        namespace_create = Mock(return_value=None)
        namespace_check = Mock(return_value=True)

        pod_body = parse_pod(ResourceInstance(None, {"kind": "Pod", "status": {"phase": "Completed"}}))
        kpod_get = Mock(return_value=pod_body)

        create_pod_body = parse_pod(
            ResourceInstance(None, {"kind": "Pod", "metadata": {"name": "bkapp-foo-stag-slug-pod"}})
        )
        kpod_create_or_update = Mock(return_value=(create_pod_body, True))

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get_or_create", namespace_create),
            patch("paas_wl.infras.resources.base.kres.KNamespace.wait_for_default_sa", namespace_check),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.create_or_update", kpod_create_or_update),
            patch("paas_wl.bk_app.deploy.app_res.controllers.WaitPodDelete.wait"),
        ):
            build_handler.build_slug(template=pod_template)
            assert kpod_create_or_update.called

            _args, kwargs = kpod_create_or_update.call_args_list[0]
            body = kwargs.get("body")
            container_spec = body["spec"]["containers"][0]

            if build_debug:
                assert "startupProbe" in container_spec
                assert container_spec["startupProbe"]["exec"]["command"] == ["test", "-f", "/tmp/build-done"]
                assert "readinessProbe" in container_spec
                assert container_spec["readinessProbe"]["exec"]["command"] == [
                    "test",
                    "-f",
                    "/tmp/build-result-success",
                ]
                assert body["metadata"]["labels"].get("build-debug") == "true"
            else:
                assert "startupProbe" not in container_spec
                assert "readinessProbe" not in container_spec
                assert "build-debug" not in body["metadata"]["labels"]

    def test_build_slug_debug_force_delete_existing(self, build_handler, wl_app):
        """已存在的 debug Pod 应被无条件强制删除 (即使 Phase 为 Running)."""
        namespace_create = Mock(return_value=None)
        namespace_check = Mock(return_value=True)

        # 已存在的 Pod 带有 build-debug label
        existing_debug_pod = ResourceInstance(
            None,
            {
                "kind": "Pod",
                "metadata": {"name": "foo", "labels": {"build-debug": "true"}},
                "status": {"phase": "Running", "startTime": timezone.now().isoformat()},
            },
        )
        kpod_get = Mock(return_value=existing_debug_pod)
        kpod_delete = Mock(return_value=None)

        create_pod_body = parse_pod(
            ResourceInstance(None, {"kind": "Pod", "metadata": {"name": "bkapp-foo-stag-slug-pod"}})
        )
        kpod_create_or_update = Mock(return_value=(create_pod_body, True))

        with (
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get_or_create", namespace_create),
            patch("paas_wl.infras.resources.base.kres.KNamespace.wait_for_default_sa", namespace_check),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.get", kpod_get),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.delete", kpod_delete),
            patch("paas_wl.infras.resources.base.kres.NameBasedOperations.create_or_update", kpod_create_or_update),
            patch("paas_wl.bk_app.deploy.app_res.controllers.WaitPodDelete.wait"),
        ):
            build_handler.build_slug(template=self._make_template(wl_app, build_debug=True))
            # 旧 debug Pod 被删除, 新 Pod 被创建
            assert kpod_delete.called
            assert kpod_create_or_update.called
