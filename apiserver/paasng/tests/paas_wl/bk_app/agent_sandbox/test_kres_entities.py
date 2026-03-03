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

import pytest

from paas_wl.bk_app.agent_sandbox.constants import DAEMON_BIND_PORT, DAEMON_COMMAND, DEFAULT_IMAGE
from paas_wl.bk_app.agent_sandbox.kres_entities import (
    AgentSandbox,
    AgentSandboxKresApp,
    AgentSandboxService,
    agent_sandbox_kmodel,
    agent_sandbox_svc_kmodel,
)
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from tests.paas_wl.utils.basic import random_resource_name
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


DEFAULT_WORKDIR = "/workspace"


class TestAgentSandboxKresApp:
    """Test AgentSandboxKresApp entity."""

    def test_init(self):
        """Test AgentSandboxKresApp initialization."""
        sbx_app = AgentSandboxKresApp(
            paas_app_id="demo-app",
            tenant_id=DEFAULT_TENANT_ID,
            target=CLUSTER_NAME_FOR_TESTING,
        )

        assert sbx_app.paas_app_id == "demo-app"
        assert sbx_app.tenant_id == DEFAULT_TENANT_ID
        assert sbx_app.target == CLUSTER_NAME_FOR_TESTING
        assert sbx_app.namespace == "bk-agent-sbx-demo-app"

    def test_get_kube_api_client(self):
        """Test getting kubernetes API client."""
        sbx_app = AgentSandboxKresApp(
            paas_app_id="demo-app",
            tenant_id=DEFAULT_TENANT_ID,
            target=CLUSTER_NAME_FOR_TESTING,
        )

        # Should return a valid client context manager
        with sbx_app.get_kube_api_client() as client:
            assert client is not None

    def test_get_kube_api_client_no_target(self):
        """Test that missing target raises ValueError."""
        sbx_app = AgentSandboxKresApp(
            paas_app_id="demo-app",
            tenant_id=DEFAULT_TENANT_ID,
            target="",
        )

        with pytest.raises(ValueError, match="missing valid target"):
            sbx_app.get_kube_api_client()


class TestAgentSandbox:
    """Test AgentSandbox entity."""

    @pytest.fixture()
    def sbx_app(self) -> AgentSandboxKresApp:
        """Create an AgentSandboxKresApp for testing."""
        return AgentSandboxKresApp(
            paas_app_id="demo-sbx",
            tenant_id=DEFAULT_TENANT_ID,
            target=CLUSTER_NAME_FOR_TESTING,
        )

    def test_create(self, sbx_app: AgentSandboxKresApp):
        """Test AgentSandbox.create factory method."""
        sbx = AgentSandbox.create(
            sbx_app,
            name="test-sandbox",
            sandbox_id="abc123",
            workdir="/app",
            snapshot=DEFAULT_IMAGE,
            env={"FOO": "BAR"},
            snapshot_entrypoint=["python", "-m", "http.server"],
        )

        assert sbx.name == "test-sandbox"
        assert sbx.sandbox_id == "abc123"
        assert sbx.workdir == "/app"
        assert sbx.image == DEFAULT_IMAGE
        assert sbx.env == {"FOO": "BAR"}
        assert sbx.command == DAEMON_COMMAND
        assert sbx.args == ["python", "-m", "http.server"]


class TestAgentSandboxService:
    """Test AgentSandboxService entity."""

    @pytest.fixture()
    def sbx_app(self) -> AgentSandboxKresApp:
        """Create an AgentSandboxKresApp for testing."""
        return AgentSandboxKresApp(
            paas_app_id="demo-sbx",
            tenant_id=DEFAULT_TENANT_ID,
            target=CLUSTER_NAME_FOR_TESTING,
        )

    @pytest.fixture()
    def sandbox(self, sbx_app: AgentSandboxKresApp) -> AgentSandbox:
        """Create an AgentSandbox for testing."""
        return AgentSandbox.create(
            sbx_app,
            name="test-sandbox",
            sandbox_id="abc123",
            workdir=DEFAULT_WORKDIR,
            snapshot=DEFAULT_IMAGE,
        )

    def test_create(self, sandbox: AgentSandbox):
        """Test AgentSandboxService.create factory method."""
        svc = AgentSandboxService.create(sandbox, node_port=30001)

        assert svc.name == sandbox.name
        assert len(svc.ports) == 1
        assert svc.ports[0].name == "daemon"
        assert svc.ports[0].port == DAEMON_BIND_PORT
        assert svc.ports[0].target_port == DAEMON_BIND_PORT
        assert svc.ports[0].node_port == 30001


class TestAgentSandboxKModel:
    """Test AgentSandbox kmodel operations with real K8s cluster."""

    @pytest.fixture()
    def sbx_app(self, namespace_maker) -> AgentSandboxKresApp:
        """Create an AgentSandboxKresApp for testing and ensure namespace exists."""
        sbx_app = AgentSandboxKresApp(
            paas_app_id=random_resource_name(),
            tenant_id=DEFAULT_TENANT_ID,
            target=CLUSTER_NAME_FOR_TESTING,
        )
        return sbx_app

    @pytest.fixture()
    def sandbox(self, sbx_app: AgentSandboxKresApp) -> AgentSandbox:
        """Create an AgentSandbox for testing."""
        sbx = AgentSandbox.create(
            sbx_app,
            name=random_resource_name(),
            sandbox_id="abc123",
            workdir="/app",
            snapshot=DEFAULT_IMAGE,
            env={"FOO": "BAR"},
        )
        return sbx

    def test_sandbox_create_and_get(self, namespace_maker, sbx_app, sandbox):
        """Create a sandbox and get it back to test the kmodel functionality."""
        namespace_maker.make(sbx_app.namespace)

        # test sandbox pod
        agent_sandbox_kmodel.create(sandbox)
        created_sbx = agent_sandbox_kmodel.get(sbx_app, sandbox.name)
        assert created_sbx.name == sandbox.name
        assert created_sbx.sandbox_id == sandbox.sandbox_id
        assert created_sbx.workdir == sandbox.workdir
        assert created_sbx.image == sandbox.image
        assert created_sbx.env == sandbox.env

        # test sandbox service
        svc = AgentSandboxService.create(sandbox, node_port=30001)
        agent_sandbox_svc_kmodel.create(svc)

        created_svc = agent_sandbox_svc_kmodel.get(sbx_app, svc.name)
        assert created_svc.name == svc.name
        assert len(created_svc.ports) == len(svc.ports)
        assert created_svc.ports[0].name == svc.ports[0].name
        assert created_svc.ports[0].port == svc.ports[0].port
        assert created_svc.ports[0].target_port == svc.ports[0].target_port
        assert created_svc.ports[0].node_port == svc.ports[0].node_port
