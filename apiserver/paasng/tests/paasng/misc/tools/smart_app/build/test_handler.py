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

from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paasng.misc.tools.smart_app.build.handler import (
    ContainerRuntimeSpec,
    SecurityContext,
    SmartBuilderTemplate,
    SmartBuildHandler,
)


@pytest.fixture
def mock_client():
    """Mock Kubernetes client"""

    return mock.Mock()


@pytest.fixture
def smart_build_handler(mock_client):
    """SmartBuildHandler instance"""

    return SmartBuildHandler(mock_client)


@pytest.fixture
def basic_runtime_spec():
    """Basic container runtime specification"""

    return ContainerRuntimeSpec(
        image="blueking/test:latest",
        envs={"FOO": "bar", "BAZ": "qux"},
        image_pull_policy=ImagePullPolicy.IF_NOT_PRESENT,
        resources={"limits": {"cpu": "1", "memory": "1Gi"}},
    )


@pytest.fixture
def basic_template(basic_runtime_spec):
    """Basic SmartBuilderTemplate instance"""

    return SmartBuilderTemplate(
        name="test_builder",
        namespace="smart-app-builder",
        runtime=basic_runtime_spec,
        schedule=Schedule(cluster_name="test-cluster", tolerations=[], node_selector={}),
    )


class TestSmartBuildHandler:
    """Test SmartBuildHandler core logic"""

    def test_construct_pod_body_basic(self, smart_build_handler, basic_template):
        """Test _construct_pod_body with basic configuration"""

        pod_body = smart_build_handler._construct_pod_body("test-pod", basic_template)

        # Verify basic structure
        assert pod_body["apiVersion"] == "v1"
        assert pod_body["kind"] == "Pod"

        # Verify metadata
        metadata = pod_body["metadata"]
        assert metadata["name"] == "test-pod"
        assert metadata["namespace"] == "smart-app-builder"
        assert metadata["labels"]["pod_selector"] == "test-pod"
        assert metadata["labels"]["category"] == "smart-app-builder"

        # Verify spec
        spec = pod_body["spec"]
        assert spec["restartPolicy"] == "Never"
        assert spec["nodeSelector"] == {}
        assert spec["imagePullSecrets"] == []

        # Verify container
        container = spec["containers"][0]
        assert container["name"] == "test-pod"
        assert container["image"] == "blueking/test:latest"
        assert container["imagePullPolicy"] == "IfNotPresent"
        assert container["resources"] == {"limits": {"cpu": "1", "memory": "1Gi"}}
        assert container["securityContext"]["privileged"] is True

        # Verify environment variables
        env_list = container["env"]
        assert len(env_list) == 2
        env_dict = {e["name"]: e["value"] for e in env_list}
        assert env_dict == {"FOO": "bar", "BAZ": "qux"}

    def test_construct_pod_body_with_tolerations(self, smart_build_handler):
        """Test _construct_pod_body with tolerations"""

        template = SmartBuilderTemplate(
            name="test_builder",
            namespace="smart-app-builder",
            runtime=ContainerRuntimeSpec(image="blueking/test:latest"),
            schedule=Schedule(
                cluster_name="test-cluster",
                tolerations=[
                    {"key": "test", "operator": "Equal", "value": "value"},
                    {"key": "dedicated", "operator": "Exists"},
                ],
                node_selector={"node-type": "builder", "zone": "az1"},
            ),
        )

        pod_body = smart_build_handler._construct_pod_body("test-pod", template)

        assert "tolerations" in pod_body["spec"]
        assert len(pod_body["spec"]["tolerations"]) == 2
        assert pod_body["spec"]["tolerations"][0] == {"key": "test", "operator": "Equal", "value": "value"}
        assert pod_body["spec"]["nodeSelector"] == {"node-type": "builder", "zone": "az1"}

    def test_construct_pod_body_without_tolerations(self, smart_build_handler, basic_template):
        """Test _construct_pod_body without tolerations"""

        pod_body = smart_build_handler._construct_pod_body("test-pod", basic_template)

        # When tolerations is empty, the key should not exist in pod_body
        assert "tolerations" not in pod_body["spec"]

    def test_construct_pod_body_with_empty_envs(self, smart_build_handler):
        """Test _construct_pod_body with empty environment variables"""

        template = SmartBuilderTemplate(
            name="test_builder",
            namespace="smart-app-builder",
            runtime=ContainerRuntimeSpec(image="blueking/test:latest", envs={}),
            schedule=Schedule(cluster_name="test-cluster", tolerations=[], node_selector={}),
        )

        pod_body = smart_build_handler._construct_pod_body("test-pod", template)

        assert pod_body["spec"]["containers"][0]["env"] == []

    def test_construct_pod_body_with_security_context(self, smart_build_handler):
        """Test _construct_pod_body with custom security context"""

        template = SmartBuilderTemplate(
            name="test_builder",
            namespace="smart-app-builder",
            runtime=ContainerRuntimeSpec(
                image="blueking/test:latest",
                securityContext=SecurityContext(privileged=False),
            ),
            schedule=Schedule(cluster_name="test-cluster", tolerations=[], node_selector={}),
        )

        pod_body = smart_build_handler._construct_pod_body("test-pod", template)

        assert pod_body["spec"]["containers"][0]["securityContext"]["privileged"] is False
