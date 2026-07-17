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
endpoint. It mounts the CFS/NFS root and exposes jailed file operations under ``/files/*``:
list / stat / preview are ``GET`` with query params, archive is ``POST`` with a JSON body,
delete is ``DELETE`` with query params.

All path-taking operations take a ``base_path`` (the jail root, computed by apiserver as
``app/{volume_uuid_hex}``) plus a user-controlled ``rel_path``; the daemon enforces the jail.
"""

from functools import lru_cache
from typing import Any, NotRequired, Self, TypedDict

import requests

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


class FileItem(TypedDict):
    path: str
    name: str
    is_dir: bool
    size: int
    modified_at: str
    mime: str


class ListResult(TypedDict):
    total: int
    items: list[FileItem]


class StatResult(TypedDict):
    exists: bool
    path: str
    size: NotRequired[int]
    modified_at: NotRequired[str]
    mime: NotRequired[str]


class ArchiveResult(TypedDict):
    sha256: str
    size: int
    mtime: str


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
    ) -> ListResult:
        """List files under base_path/rel_path with pagination."""
        params: dict[str, Any] = {
            "base_path": base_path,
            "rel_path": rel_path,
            "page": page,
            "page_size": page_size,
        }
        # 与 daemon 约定一致: 布尔 query 用小写 "true", 仅在开启时下发(false 为默认, 省略)
        if recursive:
            params["recursive"] = "true"
        return self._request("GET", "/files/list", params=params).json()

    def stat(self, base_path: str, rel_path: str) -> StatResult:
        """Return metadata of base_path/rel_path."""
        params = {"base_path": base_path, "rel_path": rel_path}
        return self._request("GET", "/files/stat", params=params).json()

    def preview(self, base_path: str, rel_path: str, max_bytes: int | None = None) -> tuple[bytes, bool]:
        """Preview the first bytes of a text file, returned as UTF-8.

        :returns: ``(content, truncated)`` where ``truncated`` reflects the daemon's ``X-Truncated`` header.
        :raises SandboxFileNotPreviewable: When the file is not a previewable text type.
        """
        params: dict[str, Any] = {"base_path": base_path, "rel_path": rel_path}
        if max_bytes is not None:
            params["max_bytes"] = max_bytes
        resp = self._request("GET", "/files/preview", params=params)
        truncated = resp.headers.get("X-Truncated", "false").lower() == "true"
        return resp.content, truncated

    def archive(self, base_path: str, rel_path: str, upload_url: str) -> ArchiveResult:
        """Archive a file to bkrepo via the presigned upload URL."""
        payload = {"base_path": base_path, "rel_path": rel_path, "upload_url": upload_url}
        return self._request("POST", "/files/archive", json=payload).json()

    def delete(self, base_path: str, rel_path: str) -> None:
        """Delete a single file. Deleting a non-existent file is idempotent (success)."""
        params = {"base_path": base_path, "rel_path": rel_path}
        self._request("DELETE", "/files", params=params)

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


@lru_cache(maxsize=1)
def get_resident_daemon_client() -> ResidentDaemonClient:
    """Build a ResidentDaemonClient from platform settings."""
    from django.conf import settings

    return ResidentDaemonClient(
        base_url=settings.AGENT_SANDBOX_RESIDENT_DAEMON_URL,
        token=settings.AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN,
    )
