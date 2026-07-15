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

"""HTTP client for the resident sandbox daemon.

Unlike ``SandboxDaemonClient`` (which talks to a per-sandbox daemon through the Sandbox
Router), the resident daemon is a long-lived platform component reachable at a fixed
endpoint. It mounts the CFS root and exposes jailed file operations over ``/files/cfs/*``.

All path-taking operations take a ``base_path`` (the jail root, computed by apiserver as
``app/{volume_uuid_hex}``) plus a user-controlled ``rel_path``; the daemon enforces the jail.
"""

from typing import Any, Self

import requests
from attrs import define

from .exceptions import (
    SandboxArchiveFailed,
    SandboxDaemonAPIError,
    SandboxFileNotFound,
    SandboxFileNotPreviewable,
    SandboxFileTooLarge,
    SandboxServiceNotReady,
)

# Default timeout for HTTP requests (in seconds)
DEFAULT_REQUEST_TIMEOUT = 60


@define
class PreviewResult:
    """Result of a text preview from the resident daemon."""

    content: bytes
    truncated: bool


class ResidentDaemonClient:
    """HTTP client for the resident sandbox daemon, reachable at a fixed cluster endpoint.

    :param base_url: The resident daemon URL (e.g., "http://bkpaas-sandbox-resident-daemon:8000").
    :param token: The static shared token for authenticating with the daemon.
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.timeout = DEFAULT_REQUEST_TIMEOUT
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"

    def list(
        self,
        base_path: str,
        rel_path: str = "",
        recursive: bool = False,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """List files under base_path/rel_path with pagination.

        :returns: A dict of {"total": int, "items": [FileItem, ...]}.
        """
        payload = {
            "base_path": base_path,
            "rel_path": rel_path,
            "recursive": recursive,
            "page": page,
            "page_size": page_size,
        }
        return self._request("POST", "/files/cfs/list", json=payload).json()

    def stat(self, base_path: str, rel_path: str) -> dict:
        """Return metadata of base_path/rel_path.

        :returns: A dict with "exists"; when exists, also "size", "modified_at", "mime".
        """
        payload = {"base_path": base_path, "rel_path": rel_path}
        return self._request("POST", "/files/cfs/stat", json=payload).json()

    def preview(self, base_path: str, rel_path: str, max_bytes: int | None = None) -> PreviewResult:
        """Preview the first bytes of a text file, returned as UTF-8.

        :raises SandboxFileNotPreviewable: When the file is not a previewable text type.
        """
        payload: dict = {"base_path": base_path, "rel_path": rel_path}
        if max_bytes is not None:
            payload["max_bytes"] = max_bytes
        resp = self._request("POST", "/files/cfs/preview", json=payload)
        truncated = resp.headers.get("X-Truncated", "false").lower() == "true"
        return PreviewResult(content=resp.content, truncated=truncated)

    def archive(self, base_path: str, rel_path: str, upload_url: str) -> dict:
        """Archive a file to bkrepo via the presigned upload URL.

        :returns: A dict of {"sha256": str, "size": int, "mtime": str}.
        """
        payload = {"base_path": base_path, "rel_path": rel_path, "upload_url": upload_url}
        return self._request("POST", "/files/cfs/archive", json=payload).json()

    def delete(self, base_path: str, rel_path: str) -> None:
        """Delete a single file. Deleting a non-existent file is idempotent (success)."""
        params = {"base_path": base_path, "rel_path": rel_path}
        self._request("DELETE", "/files/cfs", params=params)

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def _request(self, method: str, path: str, timeout: int | None = None, **kwargs: Any) -> requests.Response:
        """Send an HTTP request with unified error handling.

        Maps daemon status codes to domain exceptions:
        404 -> SandboxFileNotFound, 413 -> SandboxFileTooLarge, 415 -> SandboxFileNotPreviewable,
        502 -> SandboxServiceNotReady, 5xx on archive -> SandboxArchiveFailed, others -> SandboxDaemonAPIError.
        """
        try:
            resp = self._session.request(
                method,
                f"{self.base_url}{path}",
                timeout=timeout or self.timeout,
                **kwargs,
            )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code
            if status_code == 404:
                raise SandboxFileNotFound(f"file not found on {path}")
            if status_code == 413:
                raise SandboxFileTooLarge(f"file too large on {path}")
            if status_code == 415:
                raise SandboxFileNotPreviewable(f"file not previewable on {path}")
            # 归档路径上, daemon 读 CFS 文件或 PUT 到 bkrepo 失败时返回 502(BadGateway),
            # 归为归档失败(常驻 daemon 无 Router, 502 不代表服务未就绪)
            if path.endswith("/archive") and status_code >= 500:
                raise SandboxArchiveFailed(f"archive failed with HTTP {status_code}")
            if status_code == 502:
                raise SandboxServiceNotReady("resident daemon service is not ready")
            raise SandboxDaemonAPIError(f"HTTP error {status_code} on {path}")
        except requests.RequestException as exc:
            raise SandboxDaemonAPIError(f"Request failed: {exc}")
        else:
            return resp

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def get_resident_daemon_client() -> ResidentDaemonClient:
    """Build a ResidentDaemonClient from platform settings."""
    from django.conf import settings

    return ResidentDaemonClient(
        base_url=settings.AGENT_SANDBOX_RESIDENT_DAEMON_URL,
        token=settings.AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN,
    )
