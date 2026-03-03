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

from unittest import mock

import pytest
import requests

from paasng.platform.agent_sandbox.daemon_client import DEFAULT_REQUEST_TIMEOUT, ExecuteResult, SandboxDaemonClient
from paasng.platform.agent_sandbox.exceptions import SandboxDaemonAPIError


class TestSandboxDaemonClient:
    """Test SandboxDaemonClient HTTP client functionality."""

    @pytest.fixture()
    def client(self) -> SandboxDaemonClient:
        """Create a SandboxDaemonClient instance for testing."""
        return SandboxDaemonClient(endpoint="127.0.0.1:8000", token="test-token")

    def test_init(self, client: SandboxDaemonClient):
        """Test client initialization."""
        assert client.base_url == "http://127.0.0.1:8000"
        assert client.timeout == DEFAULT_REQUEST_TIMEOUT
        assert client._session.headers["Authorization"] == "Bearer test-token"

    def test_execute_success(self, client: SandboxDaemonClient):
        """Test successful command execution."""
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {"output": "hello\n", "exitCode": 0}

        with mock.patch.object(client._session, "request", return_value=mock_response) as mock_request:
            result = client.execute("echo hello")

            assert isinstance(result, ExecuteResult)
            assert result.output == "hello\n"
            assert result.exit_code == 0
            mock_request.assert_called_once_with(
                "POST",
                "http://127.0.0.1:8000/process/execute",
                timeout=DEFAULT_REQUEST_TIMEOUT,
                json={"command": "echo hello"},
            )

    def test_execute_with_cwd(self, client: SandboxDaemonClient):
        """Test command execution with working directory."""
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {"output": "/workspace\n", "exitCode": 0}

        with mock.patch.object(client._session, "request", return_value=mock_response) as mock_request:
            result = client.execute("pwd", cwd="/workspace")

            assert result.output == "/workspace\n"
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"]["cwd"] == "/workspace"

    def test_execute_with_timeout(self, client: SandboxDaemonClient):
        """Test command execution with custom timeout."""
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {"output": "", "exitCode": 0}

        with mock.patch.object(client._session, "request", return_value=mock_response) as mock_request:
            client.execute("sleep 10", timeout=30)

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"]["timeout"] == 30
            # Request timeout should be command timeout + 1
            assert call_kwargs["timeout"] == 31

    def test_upload_file(self, client: SandboxDaemonClient):
        """Test file upload."""
        mock_response = mock.MagicMock()

        with mock.patch.object(client._session, "request", return_value=mock_response) as mock_request:
            client.upload_file(b"file content", "/workspace/test.txt")

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == ("POST", "http://127.0.0.1:8000/files/upload")
            assert call_args[1]["data"]["destPath"] == "/workspace/test.txt"

    def test_download_file(self, client: SandboxDaemonClient):
        """Test file download."""
        mock_response = mock.MagicMock()
        mock_response.content = b"downloaded content"

        with mock.patch.object(client._session, "request", return_value=mock_response) as mock_request:
            content = client.download_file("/workspace/test.txt")

            assert content == b"downloaded content"
            mock_request.assert_called_once_with(
                "GET",
                "http://127.0.0.1:8000/files/download",
                timeout=DEFAULT_REQUEST_TIMEOUT,
                params={"path": "/workspace/test.txt"},
            )

    def test_delete_file(self, client: SandboxDaemonClient):
        """Test file deletion."""
        mock_response = mock.MagicMock()

        with mock.patch.object(client._session, "request", return_value=mock_response) as mock_request:
            client.delete_file("/workspace/test.txt")

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"]["path"] == "/workspace/test.txt"
            assert "recursive" not in call_kwargs["params"]

    def test_delete_file_recursive(self, client: SandboxDaemonClient):
        """Test recursive file/folder deletion."""
        mock_response = mock.MagicMock()

        with mock.patch.object(client._session, "request", return_value=mock_response) as mock_request:
            client.delete_file("/workspace/folder", recursive=True)

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"]["recursive"] == "true"

    def test_create_folder(self, client: SandboxDaemonClient):
        """Test folder creation."""
        mock_response = mock.MagicMock()

        with mock.patch.object(client._session, "request", return_value=mock_response) as mock_request:
            client.create_folder("/workspace/new_folder", mode="0755")

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"]["path"] == "/workspace/new_folder"
            assert call_kwargs["json"]["mode"] == "0755"

    def test_request_timeout_error(self, client: SandboxDaemonClient):
        """Test that timeout errors are wrapped in SandboxDaemonAPIError."""
        with (
            mock.patch.object(client._session, "request", side_effect=requests.Timeout("timeout")),
            pytest.raises(SandboxDaemonAPIError, match="timed out"),
        ):
            client.execute("echo hello")

    def test_request_http_error(self, client: SandboxDaemonClient):
        """Test that HTTP errors are wrapped in SandboxDaemonAPIError."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal server error"}

        http_error = requests.HTTPError(response=mock_response)
        with (
            mock.patch.object(client._session, "request", side_effect=http_error),
            pytest.raises(SandboxDaemonAPIError, match="HTTP error 500"),
        ):
            client.execute("echo hello")

    def test_request_connection_error(self, client: SandboxDaemonClient):
        """Test that connection errors are wrapped in SandboxDaemonAPIError."""
        with (
            mock.patch.object(client._session, "request", side_effect=requests.ConnectionError("connection refused")),
            pytest.raises(SandboxDaemonAPIError, match="Request failed"),
        ):
            client.execute("echo hello")

    def test_context_manager(self):
        """Test client as context manager."""
        with SandboxDaemonClient("127.0.0.1:8000", "token") as client:
            assert client.base_url == "http://127.0.0.1:8000"

    def test_close(self, client: SandboxDaemonClient):
        """Test client close method."""
        with mock.patch.object(client._session, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()


class TestExecuteResult:
    """Test ExecuteResult data class."""

    def test_execute_result_attrs(self):
        """Test ExecuteResult attributes."""
        result = ExecuteResult(output="hello", exit_code=0)
        assert result.output == "hello"
        assert result.exit_code == 0

    def test_execute_result_with_empty_output(self):
        """Test ExecuteResult with empty output."""
        result = ExecuteResult(output="", exit_code=1)
        assert result.output == ""
        assert result.exit_code == 1
