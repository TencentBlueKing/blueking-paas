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

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAgentSandboxFSViewSet:
    """Test cases for Agent Sandbox file system APIs using mocked sandbox client."""

    def test_file_lifecycle(self, api_client: APIClient, sandbox_id_with_mock: str) -> None:
        """Verify folder/file lifecycle APIs work end-to-end with mocked sandbox.

        :param api_client: The API client fixture.
        :param sandbox_id_with_mock: The sandbox UUID with mocked client backend.
        """
        folder_path = f"/workspace/{uuid.uuid4().hex[:8]}"
        file_path = f"{folder_path}/hello.txt"
        payload = b"hello-agent-sandbox\n"

        # Create a folder first
        create_folder_url = reverse("agent_sandbox.fs.create_folder", kwargs={"sandbox_id": sandbox_id_with_mock})
        create_folder_resp = api_client.post(create_folder_url, data={"path": folder_path, "mode": "755"})
        assert create_folder_resp.status_code == status.HTTP_204_NO_CONTENT

        # Upload a file into the created folder
        upload_file_url = reverse("agent_sandbox.fs.upload_file", kwargs={"sandbox_id": sandbox_id_with_mock})
        upload_file_resp = api_client.post(
            upload_file_url,
            data={"path": file_path, "file": SimpleUploadedFile("hello.txt", payload)},
            format="multipart",
        )
        assert upload_file_resp.status_code == status.HTTP_204_NO_CONTENT

        # Download the uploaded file
        download_file_url = reverse("agent_sandbox.fs.download_file", kwargs={"sandbox_id": sandbox_id_with_mock})
        download_file_resp = api_client.get(download_file_url, data={"path": file_path})
        assert download_file_resp.status_code == status.HTTP_200_OK
        assert download_file_resp.content == payload
        assert download_file_resp["Content-Disposition"] == 'attachment; filename="hello.txt"'

        # Delete the file
        delete_file_url = reverse("agent_sandbox.fs.delete_file", kwargs={"sandbox_id": sandbox_id_with_mock})
        delete_file_resp = api_client.post(delete_file_url, data={"path": file_path})
        assert delete_file_resp.status_code == status.HTTP_204_NO_CONTENT

    def test_download_missing_file(self, api_client: APIClient, sandbox_id_with_mock: str) -> None:
        """Verify downloading a missing file returns the expected error code.

        :param api_client: The API client fixture.
        :param sandbox_id_with_mock: The sandbox UUID with mocked client backend.
        """
        download_file_url = reverse("agent_sandbox.fs.download_file", kwargs={"sandbox_id": sandbox_id_with_mock})
        resp = api_client.get(download_file_url, data={"path": f"/workspace/{uuid.uuid4().hex[:8]}.txt"})

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "AGENT_SANDBOX_FILE_OPERATION_FAILED"
