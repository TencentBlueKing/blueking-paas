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

import uuid
from typing import Iterator
from unittest import mock

import pytest

from paas_wl.bk_app.agent_sandbox.kres_entities import AgentSandbox, AgentSandboxKresApp
from paasng.platform.agent_sandbox.daemon_client import ExecuteResult
from paasng.platform.agent_sandbox.sandbox import KubernetesPodSandbox

# The default working directory in sandbox container
DEFAULT_WORKDIR = "/workspace"


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version(skip_if_old_k8s_version):
    """Auto-apply shared k8s version skip guard for agent_sandbox tests."""


@pytest.fixture(scope="session", autouse=True)
def _mock_daemon_host_port() -> Iterator[None]:
    """Mock find_available_port and find_available_host for sandbox creation tests."""
    with (
        mock.patch("paasng.platform.agent_sandbox.models.find_available_port", return_value=30001),
        mock.patch("paasng.platform.agent_sandbox.models.find_available_host", return_value="192.168.1.1"),
    ):
        yield


class StubDaemonClient:
    """Stub implementation of SandboxDaemonClient for testing.

    This stub simulates a daemon service running inside a sandbox pod,
    providing in-memory file system and command execution capabilities.
    """

    def __init__(self, endpoint: str = "127.0.0.1:8000", token: str = "test-token"):
        self.endpoint = endpoint
        self.token = token
        self.timeout = 60

        # In-memory file system storage: {path: content_bytes}
        self._files: dict[str, bytes] = {}
        # In-memory folder storage: set of folder paths
        self._folders: set[str] = {DEFAULT_WORKDIR}
        # Current working directory
        self._cwd: str = DEFAULT_WORKDIR

    def execute(self, command: str, cwd: str | None = None, timeout: int | None = None) -> ExecuteResult:
        """Execute a command and return simulated result.

        Supports basic commands: pwd, echo, test, python -c, export
        """
        cwd = cwd or self._cwd

        # Handle pwd command
        if command.strip() == "pwd":
            return ExecuteResult(output=cwd + "\n", exit_code=0)

        # Default: command not recognized, return success
        return ExecuteResult(output="", exit_code=0)

    def upload_file(self, file_content: bytes, dest_path: str, timeout: int | None = None) -> None:
        """Upload a file to the in-memory storage."""
        self._files[dest_path] = file_content

    def download_file(self, path: str, timeout: int | None = None) -> bytes:
        """Download a file from the in-memory storage."""
        if path not in self._files:
            from paasng.platform.agent_sandbox.exceptions import SandboxDaemonAPIError

            raise SandboxDaemonAPIError(f"File not found: {path}")
        return self._files[path]

    def delete_file(self, path: str, recursive: bool = False) -> None:
        """Delete a file or folder from the in-memory storage."""
        if path in self._files:
            del self._files[path]
        elif path in self._folders:
            if recursive:
                # Delete folder and all contents
                self._folders.discard(path)
                to_delete = [p for p in self._files if p.startswith(path + "/")]
                for p in to_delete:
                    del self._files[p]
            else:
                self._folders.discard(path)

    def create_folder(self, path: str, mode: str | None = None) -> None:
        """Create a folder in the in-memory storage."""
        self._folders.add(path)

    def close(self) -> None:
        """Close the client (no-op for stub)."""

    def __enter__(self) -> "StubDaemonClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class StubDaemonClientFactory:
    """Factory for creating StubDaemonClient instances with shared state.

    This allows multiple calls to daemon_client() to share the same file system state.
    """

    def __init__(self):
        self._client: StubDaemonClient | None = None

    def get_client(self, endpoint: str = "127.0.0.1:8000", token: str = "test-token") -> StubDaemonClient:
        """Get or create a StubDaemonClient instance."""
        if self._client is None:
            self._client = StubDaemonClient(endpoint, token)
        return self._client

    def reset(self) -> None:
        """Reset the factory, clearing the cached client."""
        self._client = None


@pytest.fixture()
def stub_daemon_factory() -> StubDaemonClientFactory:
    """Fixture that provides a StubDaemonClientFactory instance.

    :returns: A factory for creating stub daemon clients with shared state.
    """
    return StubDaemonClientFactory()


@pytest.fixture()
def stub_daemon_client(stub_daemon_factory: StubDaemonClientFactory) -> StubDaemonClient:
    """Fixture that provides a StubDaemonClient instance.

    :returns: A stub daemon client for testing sandbox operations.
    """
    return stub_daemon_factory.get_client()


@pytest.fixture()
def stub_kres_app(bk_app) -> AgentSandboxKresApp:
    """Fixture that provides an AgentSandboxKresApp instance for testing.

    :param bk_app: The application fixture.
    :returns: An AgentSandboxKresApp instance.
    """
    return AgentSandboxKresApp(
        paas_app_id=bk_app.code,
        tenant_id=bk_app.tenant_id,
        target="default",
    )


@pytest.fixture()
def stub_agent_sandbox(stub_kres_app: AgentSandboxKresApp) -> AgentSandbox:
    """Fixture that provides an AgentSandbox entity for testing.

    :param stub_kres_app: The kres app fixture.
    :returns: An AgentSandbox entity.
    """
    sandbox_id = uuid.uuid4().hex
    return AgentSandbox.create(
        app=stub_kres_app,
        name=f"test-sbx-{sandbox_id[:8]}",
        sandbox_id=sandbox_id,
        workdir=DEFAULT_WORKDIR,
        snapshot="python:3.11-alpine",
        env={"TEST_VAR": "test_value"},
    )


@pytest.fixture()
def stub_k8s_sandbox(
    stub_agent_sandbox: AgentSandbox,
    stub_daemon_factory: StubDaemonClientFactory,
) -> Iterator[KubernetesPodSandbox]:
    """Fixture that provides a KubernetesPodSandbox with StubDaemonClient backend.

    This fixture creates a KubernetesPodSandbox that uses StubDaemonClient
    for all daemon operations, enabling unit testing without real K8s/daemon.

    :param stub_agent_sandbox: The agent sandbox entity fixture.
    :param stub_daemon_factory: The daemon client factory fixture.
    :returns: A KubernetesPodSandbox instance with stub backend.
    """
    sandbox = KubernetesPodSandbox(
        entity=stub_agent_sandbox,
        daemon_endpoint="127.0.0.1:8000",
        daemon_token="test-token",
    )

    # Patch the daemon_client method to return stub client
    def patched_daemon_client():
        return stub_daemon_factory.get_client(sandbox.daemon_endpoint, sandbox.daemon_token)

    with mock.patch.object(sandbox, "daemon_client", patched_daemon_client):
        yield sandbox
