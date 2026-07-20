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

from typing import Any, NotRequired, TypedDict

import requests
from django.conf import settings

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


def _extract_error_detail(resp: requests.Response) -> str | None:
    """Best-effort extract the daemon's human-readable error message.

    The resident daemon returns JSON error bodies shaped as ``{"message": ..., "timestamp": ...,
    "path": ..., "method": ...}`` (see ``httputil.ErrorResponse``). Non-JSON or missing ``message``
    bodies yield ``None`` so callers can fall back to a generic message.
    """
    try:
        body = resp.json()
    except ValueError:
        return None
    if isinstance(body, dict):
        msg = body.get("message")
        if isinstance(msg, str) and msg:
            return msg
    return None


class FileItem(TypedDict):
    path: str
    name: str
    is_dir: bool
    size: int
    modified_at: str
    mime: str


class ListResult(TypedDict):
    count: int
    results: list[FileItem]


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
        is_recursive: bool = False,
        page: int = 1,
        page_size: int = 100,
    ) -> ListResult:
        """List files under base_path/rel_path with pagination."""
        payload = {
            "base_path": base_path,
            "rel_path": rel_path,
            "is_recursive": is_recursive,
            "page": page,
            "page_size": page_size,
        }
        return self._request("GET", "/files/cfs/list", params=payload).json()

    def stat(self, base_path: str, rel_path: str) -> StatResult:
        """Return metadata of base_path/rel_path."""
        payload = {"base_path": base_path, "rel_path": rel_path}
        return self._request("GET", "/files/cfs/stat", params=payload).json()

    def preview(self, base_path: str, rel_path: str, max_bytes: int | None = None) -> tuple[bytes, bool]:
        """Preview the first bytes of a text file, returned as UTF-8.

        :returns: ``(content, truncated)`` where ``truncated`` reflects the daemon's ``X-Truncated`` header.
        :raises SandboxFileNotPreviewable: When the file is not a previewable text type.
        """
        payload: dict = {"base_path": base_path, "rel_path": rel_path}
        if max_bytes is not None:
            payload["max_bytes"] = max_bytes
        resp = self._request("GET", "/files/cfs/preview", params=payload)
        truncated = resp.headers.get("X-Truncated", "false").lower() == "true"
        return resp.content, truncated

    def archive(self, base_path: str, rel_path: str, upload_url: str) -> ArchiveResult:
        """Archive a file to bkrepo via the presigned upload URL."""
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
        Each carries the daemon's human-readable ``message`` (from its JSON error body) as ``detail``.
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
            detail = _extract_error_detail(exc.response)
            if status_code == 404:
                raise SandboxFileNotFound(detail or f"file not found on {path}")
            if status_code == 413:
                raise SandboxFileTooLarge(detail or f"file too large on {path}")
            if status_code == 415:
                raise SandboxFileNotPreviewable(detail or f"file not previewable on {path}")
            if path.endswith("/archive") and status_code >= 500:
                raise SandboxArchiveFailed(detail or f"archive failed with HTTP {status_code}")
            if status_code == 502:
                raise SandboxServiceNotReady(detail or "resident daemon service is not ready")
            raise SandboxDaemonAPIError(f"HTTP error {status_code} on {path}", status_code=status_code, detail=detail)
        except requests.RequestException as exc:
            # Transport-level failure (connection refused, DNS, etc.): no response, hence no status code.
            raise SandboxDaemonAPIError(f"Request failed: {exc}")
        else:
            return resp


def get_resident_daemon_client() -> ResidentDaemonClient:
    """Build a ResidentDaemonClient from platform settings."""

    return ResidentDaemonClient(
        base_url=settings.AGENT_SANDBOX_RESIDENT_DAEMON_URL,
        token=settings.AGENT_SANDBOX_RESIDENT_DAEMON_TOKEN,
    )
