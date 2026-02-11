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

from paasng.platform.agent_sandbox.entities import ExecResult
from paasng.platform.agent_sandbox.exceptions import SandboxFileError
from paasng.platform.agent_sandbox.models import Sandbox

# The default working directory in sandbox container
DEFAULT_WORKDIR = "/workspace"


@pytest.fixture(scope="session", autouse=True)
def _skip_if_old_k8s_version(skip_if_old_k8s_version):
    """Auto-apply shared k8s version skip guard for api agent_sandbox tests."""


@pytest.fixture(scope="session", autouse=True)
def _mock_daemon_host_port() -> Iterator[None]:
    """Mock find_available_port and find_available_host for sandbox creation tests."""
    with (
        mock.patch("paasng.platform.agent_sandbox.models.find_available_port", return_value=30001),
        mock.patch("paasng.platform.agent_sandbox.models.find_available_host", return_value="192.168.1.1"),
    ):
        yield


class MockKubernetesPodSandbox:
    """Mock implementation of KubernetesPodSandbox for API testing.

    Provides in-memory file system and command execution simulation.
    """

    def __init__(self):
        # In-memory file system storage: {path: content_bytes}
        self._files: dict[str, bytes] = {}
        # In-memory folder storage: set of folder paths
        self._folders: set[str] = {DEFAULT_WORKDIR}

    def exec(
        self, cmd: list[str] | str, cwd: str | None = None, env_vars: dict | None = None, timeout: int = 60
    ) -> ExecResult:
        """Execute a command and return simulated result."""
        # Handle echo command
        if isinstance(cmd, list) and cmd and cmd[0] == "echo":
            output = " ".join(cmd[1:]) + "\n"
            return ExecResult(stdout=output, stderr="", exit_code=0)

        return ExecResult(stdout="", stderr="", exit_code=0)

    def code_run(self, content: str, language: str = "Python") -> ExecResult:
        """Run code and return simulated result."""
        return ExecResult(stdout="", stderr="", exit_code=0)

    def create_folder(self, path: str, mode: str) -> None:
        """Create a folder in the in-memory storage."""
        self._folders.add(path)

    def upload_file(self, file: bytes, remote_path: str, timeout: int = 30 * 60) -> None:
        """Upload a file to the in-memory storage."""
        self._files[remote_path] = file

    def download_file(self, remote_path: str, timeout: int = 30 * 60) -> bytes:
        """Download a file from the in-memory storage."""
        if remote_path not in self._files:
            raise SandboxFileError(f"failed to download file: File not found: {remote_path}")
        return self._files[remote_path]

    def delete_file(self, path: str, recursive: bool = False) -> None:
        """Delete a file or folder from the in-memory storage."""
        if path in self._files:
            del self._files[path]
        elif path in self._folders:
            if recursive:
                self._folders.discard(path)
                to_delete = [p for p in self._files if p.startswith(path + "/")]
                for p in to_delete:
                    del self._files[p]
            else:
                self._folders.discard(path)

    def get_logs(self, tail_lines: int | None = None, timestamps: bool = False) -> str:
        """Return simulated logs."""
        return "test log output\n"


@pytest.fixture()
def mock_k8s_sandbox() -> MockKubernetesPodSandbox:
    """Fixture that provides a MockKubernetesPodSandbox instance.

    :returns: A mock sandbox for testing sandbox operations.
    """
    return MockKubernetesPodSandbox()


@pytest.fixture()
def sandbox_record(bk_app: Any) -> Sandbox:
    """Create a Sandbox record in database for testing.

    This fixture creates a Sandbox model instance without actually provisioning
    K8s resources, suitable for API tests that mock the sandbox client.

    :param bk_app: The application fixture.
    :returns: A Sandbox model instance.
    """
    sandbox = Sandbox.objects.create(
        application=bk_app,
        name=f"api-sbx-{uuid.uuid4().hex[:8]}",
        snapshot="python:3.11-alpine",
        env_vars={"TEST_VAR": "test_value"},
        creator="test-user",
        workspace=DEFAULT_WORKDIR,
    )
    return sandbox


@pytest.fixture()
def sandbox_id_with_mock(
    sandbox_record: Sandbox,
    mock_k8s_sandbox: MockKubernetesPodSandbox,
) -> Generator[str, None, None]:
    """Fixture that provides a sandbox UUID with mocked KubernetesPodSandbox.

    This fixture creates a Sandbox record and mocks get_sandbox_client to return
    a MockKubernetesPodSandbox, enabling API tests without real K8s resources.

    :param sandbox_record: The sandbox record fixture.
    :param mock_k8s_sandbox: The mock sandbox fixture.
    :returns: The sandbox UUID string.
    """
    with mock.patch(
        "paasng.platform.agent_sandbox.views.get_sandbox_client",
        return_value=mock_k8s_sandbox,
    ):
        yield sandbox_record.uuid.hex
