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

"""Stub implementations for agent sandbox testing.

This module provides stub implementations of sandbox components for testing,
enabling unit and API tests without real K8s/daemon dependencies.
"""

from paasng.platform.agent_sandbox.daemon_client import ExecuteResult

# The default working directory in sandbox container
DEFAULT_WORKDIR = "/workspace"


class StubDaemonClient:
    """Stub implementation of SandboxDaemonClient for testing.

    This stub simulates a daemon service running inside a sandbox pod,
    providing in-memory file system and command execution capabilities.
    """

    def __init__(
        self,
        router_endpoint: str = "agent-sbx-router.example.com",
        token: str = "test-token",
        sandbox_name: str = "test-sandbox",
        namespace: str = "bk-agent-sbx-test",
    ):
        self.router_endpoint = router_endpoint
        self.token = token
        self.sandbox_name = sandbox_name
        self.namespace = namespace
        self.timeout = 60

        # In-memory file system storage: {path: content_bytes}
        self._files: dict[str, bytes] = {}
        # In-memory folder storage: set of folder paths
        self._folders: set[str] = {DEFAULT_WORKDIR}
        # Current working directory
        self._cwd: str = DEFAULT_WORKDIR

    def execute(self, command: str, cwd: str | None = None, timeout: int | None = None) -> ExecuteResult:
        """Execute a command and return simulated result.

        Supports basic commands: pwd, echo
        """
        cwd = cwd or self._cwd

        # Handle pwd command
        if command.strip() == "pwd":
            return ExecuteResult(output=cwd + "\n", exit_code=0)

        # Handle echo command (simple parsing)
        if command.strip().startswith("echo "):
            # Extract the echo content, handling quoted strings
            echo_content = command.strip()[5:]
            return ExecuteResult(output=echo_content + "\n", exit_code=0)

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

    def get_client(self) -> StubDaemonClient:
        """Get or create a StubDaemonClient instance."""
        if self._client is None:
            self._client = StubDaemonClient()
        return self._client

    def reset(self) -> None:
        """Reset the factory, clearing the cached client."""
        self._client = None
