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

from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.platform.agent_sandbox.artifact import build_bkrepo_key
from paasng.platform.agent_sandbox.exceptions import SandboxDaemonAPIError, SandboxFileNotPreviewable
from paasng.platform.agent_sandbox.models import Volume, VolumeArtifact

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def _mock_presigned_url():
    """Mock make_blob_store so archive/download URL signing does not hit bkrepo."""
    store = mock.MagicMock()
    store.generate_presigned_url.return_value = "https://bkrepo.example.com/report.html?token=xxx"
    with mock.patch("paasng.platform.agent_sandbox.artifact.make_blob_store", return_value=store):
        yield store


@pytest.fixture()
def blob_store(_mock_presigned_url):
    """Expose the mocked blob store (a MagicMock) so tests can assert on its delete_file calls.

    A leading-underscore fixture (``_mock_presigned_url``) must not be injected as a test
    parameter (PT019), so this non-underscore alias returns its value instead.
    """
    return _mock_presigned_url


@pytest.mark.usefixtures("_mock_verified_app_permission", "stub_resident_client")
class TestVolumeFileViewSet:
    """Test cases for Volume file persistence APIs using a stubbed resident daemon."""

    def test_list_and_stat(self, api_client: APIClient, volume: Volume, stub_resident_client) -> None:
        stub_resident_client.put_file(volume.storage_path, "outputs/report.html", b"<html></html>")

        list_url = reverse(
            "agent_sandbox.volume.files", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        resp = api_client.get(list_url, data={"path": "outputs"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["path"] == "outputs/report.html"

        stat_url = reverse(
            "agent_sandbox.volume.files.stat", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        resp = api_client.get(stat_url, data={"path": "outputs/report.html"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["exists"] is True
        assert resp.json()["size"] == len(b"<html></html>")

    def test_stat_missing_returns_200_exists_false(self, api_client: APIClient, volume: Volume) -> None:
        stat_url = reverse(
            "agent_sandbox.volume.files.stat", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        resp = api_client.get(stat_url, data={"path": "nope.txt"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["exists"] is False

    def test_preview(self, api_client: APIClient, volume: Volume, stub_resident_client) -> None:
        stub_resident_client.put_file(volume.storage_path, "log.txt", b"hello world")
        preview_url = reverse(
            "agent_sandbox.volume.files.preview", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        resp = api_client.get(preview_url, data={"path": "log.txt"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.content == b"hello world"
        assert resp["X-Truncated"] == "false"

    def test_preview_non_text_returns_415(self, api_client: APIClient, volume: Volume, stub_resident_client) -> None:
        with mock.patch.object(stub_resident_client, "preview", side_effect=SandboxFileNotPreviewable("nope")):
            preview_url = reverse(
                "agent_sandbox.volume.files.preview",
                kwargs={"code": volume.application.code, "volume_id": volume.uuid},
            )
            resp = api_client.get(preview_url, data={"path": "image.png"})
        assert resp.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        assert resp.json()["code"] == "AGENT_SANDBOX_FILE_NOT_PREVIEWABLE"

    def test_list_daemon_400_surfaces_as_400(
        self, api_client: APIClient, volume: Volume, stub_resident_client
    ) -> None:
        """daemon 返回 400 时应透传为 400 + 可读信息, 而非冒泡为 500。"""
        err = SandboxDaemonAPIError(
            "HTTP error 400 on /files/list", status_code=400, detail="invalid path: not allowed"
        )
        list_url = reverse(
            "agent_sandbox.volume.files", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        with mock.patch.object(stub_resident_client, "list", side_effect=err):
            resp = api_client.get(list_url, data={"path": "report.html"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "AGENT_SANDBOX_FILE_OPERATION_FAILED"
        assert "invalid path" in resp.json()["detail"]

    def test_list_daemon_500_surfaces_as_500(
        self, api_client: APIClient, volume: Volume, stub_resident_client
    ) -> None:
        """daemon 返回 5xx 时应映射为 500 错误码并记录日志。"""
        err = SandboxDaemonAPIError("HTTP error 500 on /files/list", status_code=500, detail="internal daemon error")
        list_url = reverse(
            "agent_sandbox.volume.files", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        with mock.patch.object(stub_resident_client, "list", side_effect=err):
            resp = api_client.get(list_url, data={"path": "report.html"})
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.json()["code"] == "AGENT_SANDBOX_DAEMON_API_ERROR"
        assert "internal daemon error" in resp.json()["detail"]

    @pytest.mark.usefixtures("_mock_presigned_url")
    def test_download_url_archives_and_dedupes(
        self, api_client: APIClient, volume: Volume, stub_resident_client
    ) -> None:
        stub_resident_client.put_file(volume.storage_path, "report.html", b"<html></html>")
        url = reverse(
            "agent_sandbox.volume.files.download_url",
            kwargs={"code": volume.application.code, "volume_id": volume.uuid},
        )

        resp = api_client.get(url, data={"path": "report.html"})
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        # 两个互斥 URL: 各只带自己的 flag 参数, 共用同一 presigned 基址
        assert body["download_url"].endswith("download=true")
        assert body["preview_url"].endswith("preview=true")
        assert body["download_url"].split("?")[0] == body["preview_url"].split("?")[0]
        assert "preview" not in body["download_url"]
        assert "download" not in body["preview_url"]
        assert VolumeArtifact.objects.filter(volume=volume, rel_path="report.html").count() == 1

        # 第二次请求: (mtime, size) 未变, 复用去重表记录, 不重复归档
        with mock.patch.object(stub_resident_client, "archive", wraps=stub_resident_client.archive) as spy:
            resp2 = api_client.get(url, data={"path": "report.html"})
        assert resp2.status_code == status.HTTP_200_OK
        spy.assert_not_called()
        assert VolumeArtifact.objects.filter(volume=volume, rel_path="report.html").count() == 1

    @pytest.mark.usefixtures("_mock_presigned_url")
    def test_download_url_missing_file_returns_404(self, api_client: APIClient, volume: Volume) -> None:
        url = reverse(
            "agent_sandbox.volume.files.download_url",
            kwargs={"code": volume.application.code, "volume_id": volume.uuid},
        )
        resp = api_client.get(url, data={"path": "nope.txt"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["code"] == "AGENT_SANDBOX_FILE_NOT_FOUND"

    @pytest.mark.usefixtures("_mock_presigned_url")
    def test_download_url_too_large_returns_413(
        self, api_client: APIClient, volume: Volume, stub_resident_client, settings
    ) -> None:
        settings.AGENT_SANDBOX_ARTIFACT_MAX_SIZE = 4
        stub_resident_client.put_file(volume.storage_path, "big.txt", b"way too large")
        url = reverse(
            "agent_sandbox.volume.files.download_url",
            kwargs={"code": volume.application.code, "volume_id": volume.uuid},
        )
        resp = api_client.get(url, data={"path": "big.txt"})
        assert resp.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert resp.json()["code"] == "AGENT_SANDBOX_FILE_TOO_LARGE"

    def test_delete_cleans_bkrepo_object(
        self, api_client: APIClient, volume: Volume, stub_resident_client, blob_store
    ) -> None:
        """删除文件时必须连带删除 bkrepo 对象, 否则下次重新归档会命中 "Node existed"。"""
        stub_resident_client.put_file(volume.storage_path, "report.html", b"<html></html>")
        dl_url = reverse(
            "agent_sandbox.volume.files.download_url",
            kwargs={"code": volume.application.code, "volume_id": volume.uuid},
        )
        api_client.get(dl_url, data={"path": "report.html"})  # 归档, 产生对象 + 行
        key = build_bkrepo_key(volume, "report.html")
        blob_store.reset_mock()

        del_url = reverse(
            "agent_sandbox.volume.files", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        resp = api_client.delete(f"{del_url}?path=report.html")
        assert resp.status_code == status.HTTP_200_OK
        # 删除路径应清掉 bkrepo 对象
        blob_store.delete_file.assert_called_once_with(key)
        assert not VolumeArtifact.objects.filter(volume=volume, rel_path="report.html").exists()

    @pytest.mark.usefixtures("_mock_presigned_url")
    def test_rearchive_after_delete_returns_200(
        self, api_client: APIClient, volume: Volume, stub_resident_client
    ) -> None:
        """删除后重建并重新归档不应报错(回归: bkrepo "Node existed" 400)。"""
        stub_resident_client.put_file(volume.storage_path, "report.html", b"<html></html>")
        dl_url = reverse(
            "agent_sandbox.volume.files.download_url",
            kwargs={"code": volume.application.code, "volume_id": volume.uuid},
        )
        assert api_client.get(dl_url, data={"path": "report.html"}).status_code == status.HTTP_200_OK

        del_url = reverse(
            "agent_sandbox.volume.files", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        api_client.delete(f"{del_url}?path=report.html")
        assert not VolumeArtifact.objects.filter(volume=volume, rel_path="report.html").exists()

        # 重建文件后再次归档: 旧对象已清理, 不应命中 "Node existed"
        stub_resident_client.put_file(
            volume.storage_path, "report.html", b"<html>new</html>", mtime="2026-06-24T11:00:00Z"
        )
        resp = api_client.get(dl_url, data={"path": "report.html"})
        assert resp.status_code == status.HTTP_200_OK
        assert VolumeArtifact.objects.filter(volume=volume, rel_path="report.html").count() == 1

    def test_rearchive_overwrites_stale_object(
        self, api_client: APIClient, volume: Volume, stub_resident_client, blob_store
    ) -> None:
        """内容变更后重新归档: 行存在但陈旧, PUT 前应先删除旧对象(否则 "Node existed")。"""
        stub_resident_client.put_file(volume.storage_path, "report.html", b"v1", mtime="2026-06-24T10:00:00Z")
        dl_url = reverse(
            "agent_sandbox.volume.files.download_url",
            kwargs={"code": volume.application.code, "volume_id": volume.uuid},
        )
        api_client.get(dl_url, data={"path": "report.html"})  # 归档 v1
        key = build_bkrepo_key(volume, "report.html")
        blob_store.reset_mock()

        # 内容 + mtime 变更 -> 行陈旧 -> 重新归档, PUT 前应清掉旧对象
        stub_resident_client.put_file(volume.storage_path, "report.html", b"v2", mtime="2026-06-24T11:00:00Z")
        resp = api_client.get(dl_url, data={"path": "report.html"})
        assert resp.status_code == status.HTTP_200_OK
        blob_store.delete_file.assert_called_with(key)

    @pytest.mark.usefixtures("_mock_presigned_url")
    def test_delete_is_idempotent_and_clears_artifact(
        self, api_client: APIClient, volume: Volume, stub_resident_client
    ) -> None:
        stub_resident_client.put_file(volume.storage_path, "report.html", b"<html></html>")
        VolumeArtifact.objects.create(
            volume=volume,
            rel_path="report.html",
            mtime="2026-06-24T10:23:11Z",
            size=13,
            sha256="abc",
            bkrepo_key="pv-archives/x/y/report.html",
            archived_at="2026-06-24T10:23:11Z",
            tenant_id=volume.tenant_id,
        )
        url = reverse("agent_sandbox.volume.files", kwargs={"code": volume.application.code, "volume_id": volume.uuid})

        resp = api_client.delete(f"{url}?path=report.html")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["deleted"] is True
        assert not VolumeArtifact.objects.filter(volume=volume, rel_path="report.html").exists()

        # 再次删除仍然成功(幂等)
        resp2 = api_client.delete(f"{url}?path=report.html")
        assert resp2.status_code == status.HTTP_200_OK


@pytest.mark.usefixtures("_mock_app_mismatch_permission", "stub_resident_client")
class TestVolumeFilePermission:
    """Verify app isolation: a request from a mismatched app cannot access the volume."""

    def test_list_forbidden_on_app_mismatch(self, api_client: APIClient, volume: Volume) -> None:
        list_url = reverse(
            "agent_sandbox.volume.files", kwargs={"code": volume.application.code, "volume_id": volume.uuid}
        )
        resp = api_client.get(list_url, data={"path": ""})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
