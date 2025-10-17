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

from unittest.mock import Mock, patch

import pytest

from paas_wl.infras.resources.base.exceptions import ResourceDuplicate, ResourceMissing
from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.utils.constants import PodPhase
from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paasng.misc.tools.smart_app.build.handler import (
    ContainerRuntimeSpec,
    SmartBuilderTemplate,
    SmartBuildHandler,
)


@pytest.fixture
def mock_client():
    """Mock Kubernetes client"""
    return Mock()


@pytest.fixture
def smart_build_handler(mock_client):
    """SmartBuildHandler instance"""
    return SmartBuildHandler(mock_client)


@pytest.fixture
def pod_template():
    """SmartBuilderTemplate instance"""
    return SmartBuilderTemplate(
        name="test_builder",
        namespace="smart-app-builder",
        runtime=ContainerRuntimeSpec(
            image="blueking/test:latest",
            envs={"foo": "bar"},
            image_pull_policy=ImagePullPolicy.IF_NOT_PRESENT,
            resources={"limits": {"cpu": "1", "memory": "1Gi"}},
        ),
        schedule=Schedule(cluster_name="test-cluster", tolerations=[], node_selector={}),
    )


class TestSmartBuildHandler:
    def test_normalize_builder_name(self):
        """Test normalize_builder_name method"""
        assert SmartBuildHandler.normalize_builder_name("test-name") == "test-name"
        assert SmartBuildHandler.normalize_builder_name("test_name") == "test_name"

    def test_construct_pod_body_basic(self, smart_build_handler, pod_template):
        """Test _construct_pod_body with basic configuration"""
        pod_body = smart_build_handler._construct_pod_body("test-pod", pod_template)

        assert pod_body["apiVersion"] == "v1"
        assert pod_body["kind"] == "Pod"
        assert pod_body["metadata"]["name"] == "test-pod"
        assert pod_body["metadata"]["namespace"] == "smart-app-builder"
        assert pod_body["metadata"]["labels"]["pod_selector"] == "test-pod"
        assert pod_body["metadata"]["labels"]["category"] == "smart-app-builder"

        container = pod_body["spec"]["containers"][0]
        assert container["name"] == "test-pod"
        assert container["image"] == "blueking/test:latest"
        assert container["imagePullPolicy"] == "IfNotPresent"
        assert container["env"] == [{"name": "foo", "value": "bar"}]
        assert container["resources"] == {"limits": {"cpu": "1", "memory": "1Gi"}}
        assert container["securityContext"]["privileged"] is True

        assert pod_body["spec"]["restartPolicy"] == "Never"
        assert pod_body["spec"]["nodeSelector"] == {}

    def test_construct_pod_body_with_tolerations(self, smart_build_handler):
        """Test _construct_pod_body with tolerations"""
        template = SmartBuilderTemplate(
            name="test_builder",
            namespace="smart-app-builder",
            runtime=ContainerRuntimeSpec(image="blueking/test:latest"),
            schedule=Schedule(
                cluster_name="test-cluster",
                tolerations=[{"key": "test", "operator": "Equal", "value": "value"}],
                node_selector={"node-type": "builder"},
            ),
        )

        pod_body = smart_build_handler._construct_pod_body("test-pod", template)

        assert pod_body["spec"]["tolerations"] == [{"key": "test", "operator": "Equal", "value": "value"}]
        assert pod_body["spec"]["nodeSelector"] == {"node-type": "builder"}

    def test_construct_pod_body_with_image_pull_secrets(self, smart_build_handler):
        """Test _construct_pod_body with image pull secrets"""
        template = SmartBuilderTemplate(
            name="test_builder",
            namespace="smart-app-builder",
            runtime=ContainerRuntimeSpec(
                image="blueking/test:latest",
                image_pull_secrets=[{"name": "secret1"}, {"name": "secret2"}],
            ),
            schedule=Schedule(cluster_name="test-cluster", tolerations=[], node_selector={}),
        )

        pod_body = smart_build_handler._construct_pod_body("test-pod", template)

        assert pod_body["spec"]["imagePullSecrets"] == [{"name": "secret1"}, {"name": "secret2"}]

    def test_build_pod_new_pod(self, smart_build_handler, pod_template):
        """Test build_pod when pod doesn't exist"""
        mock_pod_info = Mock()
        mock_pod_info.metadata.name = "test_builder"

        mock_kpod = Mock()
        mock_kpod.get.side_effect = ResourceMissing("Pod", "test_builder")
        mock_kpod.create_or_update.return_value = (mock_pod_info, True)

        with patch("paasng.misc.tools.smart_app.build.handler.KPod", return_value=mock_kpod):
            result = smart_build_handler.build_pod(pod_template)

            assert result == "test_builder"
            mock_kpod.get.assert_called_once_with("test_builder", namespace="smart-app-builder")
            mock_kpod.create_or_update.assert_called_once()

    def test_build_pod_existing_completed_pod(self, smart_build_handler, pod_template):
        """Test build_pod when existing pod is completed"""
        completed_pod = Mock()
        completed_pod.status.phase = PodPhase.SUCCEEDED

        mock_pod_info = Mock()
        mock_pod_info.metadata.name = "test_builder"

        mock_kpod = Mock()
        mock_kpod.get.return_value = completed_pod
        mock_kpod.create_or_update.return_value = (mock_pod_info, True)

        mock_wait_pod_delete = Mock()
        mock_wait_pod_delete.wait = Mock()

        with (
            patch("paasng.misc.tools.smart_app.build.handler.KPod", return_value=mock_kpod),
            patch("paas_wl.bk_app.deploy.app_res.controllers.KPod", return_value=mock_kpod),
            patch("paas_wl.bk_app.deploy.app_res.controllers.WaitPodDelete", return_value=mock_wait_pod_delete),
        ):
            result = smart_build_handler.build_pod(pod_template)

            assert result == "test_builder"
            mock_kpod.get.assert_called_once_with("test_builder", namespace="smart-app-builder")
            mock_kpod.delete.assert_called_once()
            mock_wait_pod_delete.wait.assert_called_once()
            mock_kpod.create_or_update.assert_called_once()

    def test_build_pod_existing_running_timeout(self, smart_build_handler, pod_template):
        """Test build_pod when existing pod is running and timed out"""
        running_pod = Mock()
        running_pod.status.phase = PodPhase.RUNNING

        mock_pod_info = Mock()
        mock_pod_info.metadata.name = "test_builder"

        mock_kpod = Mock()
        mock_kpod.get.return_value = running_pod
        mock_kpod.create_or_update.return_value = (mock_pod_info, True)

        mock_wait_pod_delete = Mock()
        mock_wait_pod_delete.wait = Mock()

        # Mock timeout check to return True (timed out)
        with (
            patch("paasng.misc.tools.smart_app.build.handler.KPod", return_value=mock_kpod),
            patch("paas_wl.bk_app.deploy.app_res.controllers.KPod", return_value=mock_kpod),
            patch("paas_wl.bk_app.deploy.app_res.controllers.WaitPodDelete", return_value=mock_wait_pod_delete),
            patch.object(smart_build_handler, "check_pod_timeout", return_value=True),
        ):
            result = smart_build_handler.build_pod(pod_template)

            assert result == "test_builder"
            mock_kpod.get.assert_called_once_with("test_builder", namespace="smart-app-builder")
            mock_kpod.delete.assert_called_once()
            mock_wait_pod_delete.wait.assert_called_once()
            mock_kpod.create_or_update.assert_called_once()

    def test_build_pod_existing_running_not_timeout(self, smart_build_handler, pod_template):
        """Test build_pod when existing pod is running and not timed out"""
        running_pod = Mock()
        running_pod.status.phase = PodPhase.RUNNING
        running_pod.status.startTime = "2023-01-01T00:00:00Z"  # Add valid start time

        mock_kpod = Mock()
        mock_kpod.get.return_value = running_pod

        # Mock timeout check to return False (not timed out)
        with (
            patch("paasng.misc.tools.smart_app.build.handler.KPod", return_value=mock_kpod),
            patch.object(smart_build_handler, "check_pod_timeout", return_value=False),
            pytest.raises(ResourceDuplicate),
        ):
            smart_build_handler.build_pod(pod_template)

    def test_delete_builder(self, smart_build_handler):
        """Test delete_builder method"""
        mock_delete_finished_pod = Mock(return_value="deleted")

        with patch.object(smart_build_handler, "_delete_finished_pod", mock_delete_finished_pod):
            result = smart_build_handler.delete_builder("test-namespace", "test-name")

            assert result == "deleted"
            mock_delete_finished_pod.assert_called_once_with("test-namespace", "test-name", force=False)

    def test_wait_for_succeeded(self, smart_build_handler):
        """Test wait_for_succeeded method"""
        mock_wait_pod_succeeded = Mock(return_value=True)

        with patch.object(smart_build_handler, "_wait_pod_succeeded", mock_wait_pod_succeeded):
            result = smart_build_handler.wait_for_succeeded("test-namespace", "test-name", timeout=60)

            assert result is True
            mock_wait_pod_succeeded.assert_called_once_with(
                "test-namespace", "test-name", timeout=60, check_period=0.5
            )

    def test_wait_for_logs_readiness(self, smart_build_handler):
        """Test wait_for_logs_readiness method"""
        mock_kpod = Mock()
        mock_kpod.wait_for_status = Mock()

        with patch("paasng.misc.tools.smart_app.build.handler.KPod", return_value=mock_kpod):
            smart_build_handler.wait_for_logs_readiness("test-namespace", "test-name", timeout=30)

            mock_kpod.wait_for_status.assert_called_once_with(
                "test-name",
                {PodPhase.RUNNING, PodPhase.SUCCEEDED, PodPhase.FAILED},
                "test-namespace",
                30,
            )

    def test_get_build_log(self, smart_build_handler):
        """Test get_build_log method"""
        mock_kpod = Mock()
        mock_kpod.get_log = Mock(return_value="build logs")

        with patch("paas_wl.bk_app.deploy.app_res.controllers.KPod", return_value=mock_kpod):
            result = smart_build_handler.get_build_log("test-namespace", "test-name", timeout=30, follow=True)

            assert result == "build logs"
            mock_kpod.get_log.assert_called_once_with(
                name="test-name", namespace="test-namespace", timeout=30, follow=True
            )
