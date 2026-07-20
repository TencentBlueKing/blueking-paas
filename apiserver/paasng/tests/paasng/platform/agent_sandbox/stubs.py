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

"""Stub implementations for agent sandbox testing.

This module provides stub implementations of sandbox components for testing,
enabling unit and API tests without real K8s/daemon dependencies.
"""

from typing import Self

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

    def __enter__(self) -> Self:
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


class StubResidentDaemonClient:
    """Stub implementation of ResidentDaemonClient for testing.

    Simulates the resident daemon's jailed CFS file operations with an in-memory file system,
    keyed by (base_path, rel_path). File values are dicts of {content, mtime, size}.
    """

    def __init__(self):
        # {(base_path, rel_path): {"content": bytes, "mtime": str, "size": int}}
        self._files: dict[tuple[str, str], dict] = {}

    def put_file(self, base_path: str, rel_path: str, content: bytes, mtime: str = "2026-06-24T10:23:11Z") -> None:
        """Seed an in-memory file for tests."""
        self._files[(base_path, rel_path)] = {"content": content, "mtime": mtime, "size": len(content)}

    def list(self, base_path, rel_path="", is_recursive=False, page=1, page_size=100) -> dict:
        items = []
        for (bp, rp), meta in self._files.items():
            if bp != base_path:
                continue
            if rel_path and not rp.startswith(rel_path):
                continue
            items.append(
                {
                    "path": rp,
                    "name": rp.rsplit("/", 1)[-1],
                    "is_dir": False,
                    "size": meta["size"],
                    "modified_at": meta["mtime"],
                    "mime": "text/plain",
                    "sha256": None,
                }
            )
        return {"count": len(items), "results": items}

    def stat(self, base_path, rel_path) -> dict:
        meta = self._files.get((base_path, rel_path))
        if meta is None:
            return {"exists": False, "path": rel_path}
        return {
            "exists": True,
            "path": rel_path,
            "size": meta["size"],
            "modified_at": meta["mtime"],
            "mime": "text/plain",
        }

    def preview(self, base_path, rel_path, max_bytes=None):
        from paasng.platform.agent_sandbox.exceptions import SandboxFileNotFound

        meta = self._files.get((base_path, rel_path))
        if meta is None:
            raise SandboxFileNotFound(f"file not found: {rel_path}")
        limit = max_bytes or 65536
        content = meta["content"]
        truncated = len(content) > limit
        return content[:limit], truncated

    def archive(self, base_path, rel_path, upload_url) -> dict:
        import hashlib

        from paasng.platform.agent_sandbox.exceptions import SandboxFileNotFound

        meta = self._files.get((base_path, rel_path))
        if meta is None:
            raise SandboxFileNotFound(f"file not found: {rel_path}")
        return {
            "sha256": hashlib.sha256(meta["content"]).hexdigest(),
            "size": meta["size"],
            "mtime": meta["mtime"],
        }

    def delete(self, base_path, rel_path) -> None:
        # 幂等: 不存在也视为成功
        self._files.pop((base_path, rel_path), None)

    def close(self) -> None:
        """Close the client (no-op for stub)."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
