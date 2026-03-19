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

import uuid
from collections.abc import Generator
from typing import Any, Iterator
from unittest import mock

import pytest

from paas_wl.bk_app.agent_sandbox.kres_entities import AgentSandbox, AgentSandboxKresApp
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.sandbox import KubernetesPodSandbox
from tests.paasng.platform.agent_sandbox.stubs import DEFAULT_WORKDIR, StubDaemonClientFactory


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version(skip_if_old_k8s_version):
    """Auto-apply shared k8s version skip guard for api agent_sandbox tests."""


@pytest.fixture()
def _mock_verified_app_permission() -> Iterator[None]:
    """Mock IsAPIGWVerifiedApp to always return True for testing.

    This bypasses the API Gateway app verification check in tests.
    Use this fixture explicitly in tests that need permission bypass.
    """
    with (
        mock.patch(
            "paasng.platform.agent_sandbox.views.IsAPIGWVerifiedApp.has_permission",
            return_value=True,
        ),
        mock.patch(
            "paasng.platform.agent_sandbox.views.IsAPIGWVerifiedApp.has_object_permission",
            return_value=True,
        ),
    ):
        yield


@pytest.fixture()
def _mock_unverified_app_permission() -> Iterator[None]:
    """Mock IsAPIGWVerifiedApp to return False for has_permission.

    Use this to test scenarios where the request app is not verified.
    """
    with mock.patch(
        "paasng.platform.agent_sandbox.views.IsAPIGWVerifiedApp.has_permission",
        return_value=False,
    ):
        yield


@pytest.fixture()
def _mock_app_mismatch_permission() -> Iterator[None]:
    """Mock IsAPIGWVerifiedApp to pass has_permission but fail has_object_permission.

    Use this to test scenarios where the request app doesn't match the target app.
    """
    with (
        mock.patch(
            "paasng.platform.agent_sandbox.views.IsAPIGWVerifiedApp.has_permission",
            return_value=True,
        ),
        mock.patch(
            "paasng.platform.agent_sandbox.views.IsAPIGWVerifiedApp.has_object_permission",
            return_value=False,
        ),
    ):
        yield


@pytest.fixture()
def stub_daemon_factory() -> StubDaemonClientFactory:
    """Fixture that provides a StubDaemonClientFactory instance.

    :returns: A factory for creating stub daemon clients with shared state.
    """
    return StubDaemonClientFactory()


@pytest.fixture()
def sandbox_obj(bk_app: Any) -> Sandbox:
    """Create a Sandbox record in database for testing.

    This fixture creates a Sandbox model instance without actually provisioning
    K8s resources, suitable for API tests that mock the sandbox client.

    :param bk_app: The application fixture.
    :returns: A Sandbox model instance.
    """
    sandbox = Sandbox.objects.new(
        application=bk_app,
        name=f"api-sbx-{uuid.uuid4().hex[:8]}",
        snapshot="python:3.11-alpine",
        env_vars={"TEST_VAR": "test_value"},
        creator="test-user",
        workspace=DEFAULT_WORKDIR,
    )
    return sandbox


@pytest.fixture()
def sandbox_id(
    sandbox_obj: Sandbox,
    stub_daemon_factory: StubDaemonClientFactory,
) -> Generator[str, None, None]:
    """Fixture that provides a sandbox UUID with mocked daemon client.

    This fixture creates a Sandbox record and returns a KubernetesPodSandbox
    with StubDaemonClient backend, enabling API tests without real K8s/daemon.

    :param sandbox_obj: The sandbox record fixture.
    :param stub_daemon_factory: The daemon client factory fixture.
    :returns: The sandbox UUID string.
    """
    kres_app = AgentSandboxKresApp(
        paas_app_id=sandbox_obj.application.code,
        tenant_id=sandbox_obj.application.tenant_id,
        target=sandbox_obj.target,
    )
    entity = AgentSandbox.create(
        app=kres_app,
        name=sandbox_obj.name,
        sandbox_id=sandbox_obj.uuid.hex,
        workdir=sandbox_obj.workspace,
        snapshot=sandbox_obj.snapshot,
        env=sandbox_obj.env_vars,
    )
    sandbox_client = KubernetesPodSandbox(
        entity=entity,
        router_endpoint="agent-sbx-router.example.com",
        daemon_token=sandbox_obj.daemon_token,
    )

    def patched_daemon_client():
        return stub_daemon_factory.get_client()

    with (
        mock.patch(
            "paasng.platform.agent_sandbox.views.get_sandbox_client",
            return_value=sandbox_client,
        ),
        mock.patch.object(sandbox_client, "daemon_client", patched_daemon_client),
        # Mock get_logs since it directly calls K8s API
        mock.patch.object(sandbox_client, "get_logs", return_value="test log output\n"),
    ):
        yield sandbox_obj.uuid.hex
