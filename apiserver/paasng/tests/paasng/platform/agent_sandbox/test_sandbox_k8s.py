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

import pytest

from paasng.platform.agent_sandbox.exceptions import SandboxError, SandboxFileError

from .conftest import DEFAULT_WORKDIR

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestKubernetesPodSandboxWithStub:
    """Test KubernetesPodSandbox using StubDaemonClient backend.

    These tests verify the sandbox operations without requiring a real
    Kubernetes cluster or daemon service.
    """

    def test_exec_simple(self, stub_k8s_sandbox):
        """Test basic command execution returns correct result."""
        result = stub_k8s_sandbox.exec("pwd")
        assert result.exit_code == 0
        assert result.stdout.strip() == DEFAULT_WORKDIR

    def test_create_folder(self, stub_k8s_sandbox, stub_daemon_client):
        """Test folder creation in sandbox."""
        folder_path = f"{DEFAULT_WORKDIR}/data"
        stub_k8s_sandbox.create_folder(folder_path, mode="755")

        # Verify folder was created in stub storage
        assert folder_path in stub_daemon_client._folders

    def test_upload_and_download_file(self, stub_k8s_sandbox, stub_daemon_client):
        """Test file upload and download operations."""
        payload = b"hello\x00world\n"
        remote_path = f"{DEFAULT_WORKDIR}/blob.bin"

        # Upload file
        stub_k8s_sandbox.upload_file(payload, remote_path)

        # Verify file exists in stub storage
        assert remote_path in stub_daemon_client._files
        assert stub_daemon_client._files[remote_path] == payload

        # Download and verify content
        downloaded = stub_k8s_sandbox.download_file(remote_path)
        assert downloaded == payload

    def test_delete_file(self, stub_k8s_sandbox, stub_daemon_client):
        """Test file deletion from sandbox."""
        remote_path = f"{DEFAULT_WORKDIR}/to_delete.txt"
        payload = b"delete me"

        # First upload a file
        stub_k8s_sandbox.upload_file(payload, remote_path)
        assert remote_path in stub_daemon_client._files

        # Delete the file
        stub_k8s_sandbox.delete_file(remote_path)
        assert remote_path not in stub_daemon_client._files

    def test_download_nonexistent_file(self, stub_k8s_sandbox):
        """Test that downloading non-existent file raises error."""
        with pytest.raises(SandboxFileError, match="failed to download file"):
            stub_k8s_sandbox.download_file("/nonexistent/file.txt")

    def test_single_file_full_lifecycle(self, stub_k8s_sandbox, stub_daemon_client):
        """Test complete file lifecycle: upload, download, delete."""
        payload = b"hello\x00world\n"
        remote_path = f"{DEFAULT_WORKDIR}/lifecycle.bin"

        # Upload
        stub_k8s_sandbox.upload_file(payload, remote_path)

        # Download and verify
        downloaded = stub_k8s_sandbox.download_file(remote_path)
        assert downloaded == payload

        # Delete
        stub_k8s_sandbox.delete_file(remote_path)

        # Verify file is gone
        assert remote_path not in stub_daemon_client._files


class TestKubernetesPodSandboxCommandBuilding:
    """Test command string building functionality."""

    def test_build_command_string_simple(self, stub_k8s_sandbox):
        """Test building command string without env vars."""
        cmd_str = stub_k8s_sandbox._build_command_string("echo hello", {})
        assert cmd_str == "echo hello"

    def test_build_command_string_with_list(self, stub_k8s_sandbox):
        """Test building command string from list."""
        cmd_str = stub_k8s_sandbox._build_command_string(["echo", "hello world"], {})
        assert cmd_str == "echo 'hello world'"

    def test_build_command_string_with_env_vars(self, stub_k8s_sandbox):
        """Test building command string with environment variables."""
        cmd_str = stub_k8s_sandbox._build_command_string("echo $FOO", {"FOO": "BAR"})
        assert "export FOO=BAR" in cmd_str
        assert "echo $FOO" in cmd_str

    def test_build_command_string_with_multiple_env_vars(self, stub_k8s_sandbox):
        """Test building command string with multiple env vars."""
        cmd_str = stub_k8s_sandbox._build_command_string("cmd", {"A": "1", "B": "2"})
        assert "export" in cmd_str
        assert "A='1'" in cmd_str or "A=1" in cmd_str
        assert "B='2'" in cmd_str or "B=2" in cmd_str

    def test_validate_env_key_valid(self, stub_k8s_sandbox):
        """Test that valid env keys pass validation."""
        assert stub_k8s_sandbox._validate_env_key("FOO") == "FOO"
        assert stub_k8s_sandbox._validate_env_key("FOO_BAR") == "FOO_BAR"
        assert stub_k8s_sandbox._validate_env_key("_FOO") == "_FOO"
        assert stub_k8s_sandbox._validate_env_key("FOO123") == "FOO123"

    def test_validate_env_key_invalid(self, stub_k8s_sandbox):
        """Test that invalid env keys raise SandboxError."""
        with pytest.raises(SandboxError, match="invalid environment variable key"):
            stub_k8s_sandbox._validate_env_key("123FOO")

        with pytest.raises(SandboxError, match="invalid environment variable key"):
            stub_k8s_sandbox._validate_env_key("FOO-BAR")

        with pytest.raises(SandboxError, match="invalid environment variable key"):
            stub_k8s_sandbox._validate_env_key("FOO BAR")
