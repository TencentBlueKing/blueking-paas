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

"""HTTP client for communicating with the sandbox daemon service."""

from typing import Any

import requests
from attrs import define

from .exceptions import SandboxDaemonAPIError

# Default timeout for HTTP requests (in seconds)
DEFAULT_REQUEST_TIMEOUT = 60


@define
class ExecuteResult:
    """Result of command execution from daemon API."""

    output: str
    exit_code: int


class SandboxDaemonClient:
    """HTTP client for sandbox daemon service.

    :param endpoint: The endpoint of the daemon service (e.g., "127.0.0.1:8080").
    :param token: The authentication token for the daemon service.
    """

    def __init__(self, endpoint: str, token: str):
        self.base_url = f"http://{endpoint}"
        self.timeout = DEFAULT_REQUEST_TIMEOUT
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"

    def execute(self, command: str, cwd: str | None = None, timeout: int | None = None) -> ExecuteResult:
        """Execute a command inside the sandbox.

        :param command: The shell command to execute.
        :param cwd: The working directory for command execution.
        :param timeout: Timeout for the command execution in seconds.
        :returns: ExecuteResult containing output and exit code.
        """
        req_timeout = self.timeout

        payload: dict = {"command": command}
        if cwd:
            payload["cwd"] = cwd
        if timeout:
            payload["timeout"] = timeout
            # 在命令执行超时时间基础之上增加 1 秒, 作为接口请求的超时时间
            req_timeout = timeout + 1

        resp = self._request("POST", "/process/execute", json=payload, timeout=req_timeout)
        data = resp.json()
        return ExecuteResult(output=data.get("output", ""), exit_code=data.get("exitCode", -1))

    def upload_file(self, file_content: bytes, dest_path: str, timeout: int | None = None) -> None:
        """Upload a file to the sandbox.

        :param file_content: The file content as bytes.
        :param dest_path: The destination path in the sandbox.
        :param timeout: Timeout for the upload in seconds.
        """
        self._request(
            "POST",
            "/files/upload",
            files={"file": (dest_path.split("/")[-1], file_content)},
            data={"destPath": dest_path},
            timeout=timeout,
        )

    def download_file(self, path: str, timeout: int | None = None) -> bytes:
        """Download a file from the sandbox.

        :param path: The path of the file to download.
        :param timeout: Timeout for the download in seconds.
        :returns: The file content as bytes.
        """
        resp = self._request("GET", "/files/download", params={"path": path}, timeout=timeout)
        return resp.content

    def delete_file(self, path: str, recursive: bool = False) -> None:
        """Delete a file or folder from the sandbox.

        :param path: The path of the file or folder to delete.
        :param recursive: Enable recursive deletion for directories.
        """
        params: dict = {"path": path}
        if recursive:
            params["recursive"] = "true"

        self._request("DELETE", "/files/", params=params)

    def create_folder(self, path: str, mode: str | None = None) -> None:
        """Create a folder in the sandbox.

        :param path: The path of the folder to create.
        :param mode: Optional permission mode (e.g., "0755").
        """
        payload: dict = {"path": path}
        if mode:
            payload["mode"] = mode

        self._request("POST", "/files/folder", json=payload)

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def _request(
        self,
        method: str,
        path: str,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send HTTP request with unified error handling.

        :param method: HTTP method (GET, POST, DELETE, etc.).
        :param path: API path (e.g., "/process/execute").
        :param timeout: Request timeout in seconds.
        :param kwargs: Additional arguments passed to requests.
        :returns: Response object.
        """
        try:
            resp = self._session.request(
                method,
                f"{self.base_url}{path}",
                timeout=timeout or self.timeout,
                **kwargs,
            )
            resp.raise_for_status()

        except requests.Timeout as exc:
            raise SandboxDaemonAPIError(f"Request {path} timed out: {exc}")
        except requests.HTTPError as exc:
            raise SandboxDaemonAPIError(
                f'HTTP error {exc.response.status_code} on {path}: {exc.response.json().get("message")}'
            )
        except requests.RequestException as exc:
            raise SandboxDaemonAPIError(f"Request failed: {exc}")
        else:
            return resp

    def __enter__(self) -> "SandboxDaemonClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
