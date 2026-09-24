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

from typing import Any
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.platform.agent_sandbox.exceptions import SandboxDaemonAPIError, SandboxServiceNotReady
from paasng.platform.agent_sandbox.models import Sandbox, Volume
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.usefixtures("_mock_verified_app_permission")
class TestVolumeAPI:
    """Owner grants/revokes mount access; list still only returns owned Volumes."""

    @pytest.mark.parametrize(
        ("url_name", "method", "payload"),
        [
            pytest.param("agent_sandbox.volume.destroy", "delete", None, id="destroy"),
            pytest.param("agent_sandbox.volume.shares", "post", {"grantee_app_code": "some-app"}, id="share"),
        ],
    )
    def test_operating_other_app_volume_returns_404(
        self, *, api_client: APIClient, bk_app: Any, bk_user, url_name: str, method: str, payload: dict | None
    ) -> None:
        """Knowing another app's volume UUID is not enough to operate on it."""
        other_app = create_app(owner_username=bk_user.username)
        other_volume = Volume.objects.create(
            application=other_app,
            name="other-vol",
            tenant_id=bk_app.tenant_id,
        )

        url = reverse(url_name, kwargs={"code": bk_app.code, "volume_id": other_volume.uuid})
        resp = getattr(api_client, method)(url, data=payload, format="json")

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        other_volume.refresh_from_db()
        assert other_volume.deleted_at is None
        assert other_volume.shared_app_codes == []

    def test_share_and_unshare(self, api_client: APIClient, bk_app: Any, bk_user, volume: Volume) -> None:
        """Grant, then revoke a same-tenant application."""
        other_app = create_app(owner_username=bk_user.username)
        shares_url = reverse(
            "agent_sandbox.volume.shares",
            kwargs={"code": bk_app.code, "volume_id": volume.uuid},
        )

        resp = api_client.post(shares_url, data={"grantee_app_code": other_app.code}, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        volume.refresh_from_db()
        assert volume.shared_app_codes == [other_app.code]

        unshare_url = reverse(
            "agent_sandbox.volume.shares.destroy",
            kwargs={"code": bk_app.code, "volume_id": volume.uuid, "grantee_app_code": other_app.code},
        )
        resp = api_client.delete(unshare_url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        volume.refresh_from_db()
        assert volume.shared_app_codes == []

    def test_list_excludes_granted_volumes(self, api_client: APIClient, bk_app: Any, bk_user, volume: Volume) -> None:
        """List does not include Volumes owned by others, even after a grant."""
        other_app = create_app(owner_username=bk_user.username)
        volume.shared_app_codes = [other_app.code]
        volume.save(update_fields=["shared_app_codes", "updated"])

        url = reverse("agent_sandbox.volume", kwargs={"code": other_app.code})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        uuids = {item["uuid"] for item in resp.json()}
        assert str(volume.uuid) not in uuids


@pytest.mark.usefixtures("_mock_verified_app_permission")
class TestVolumeDestroy:
    """Volume 删除: 物理清理共享存储目录 + 软删记录"""

    @pytest.fixture()
    def url(self, bk_app: Any, volume: Volume) -> str:
        return reverse("agent_sandbox.volume.destroy", kwargs={"code": bk_app.code, "volume_id": volume.uuid})

    def test_wipes_storage_and_soft_deletes(
        self, api_client: APIClient, volume: Volume, url: str, stub_resident_client
    ) -> None:
        stub_resident_client.put_file(volume.storage_path, "outputs/report.html", b"<html></html>")

        resp = api_client.delete(url)

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert stub_resident_client.stat(volume.storage_path, "outputs/report.html")["exists"] is False
        volume.refresh_from_db()
        assert volume.deleted_at is not None

    def test_rejects_volume_in_use(
        self, api_client: APIClient, bk_app: Any, volume: Volume, url: str, stub_resident_client
    ) -> None:
        """占用校验先于物理清理: 409 时共享存储上的文件必须原样保留"""
        stub_resident_client.put_file(volume.storage_path, "outputs/report.html", b"<html></html>")
        Sandbox.objects.create(
            application=bk_app,
            name="sbx-in-use",
            snapshot="python:3.11-alpine",
            target="default",
            creator="test-user",
            tenant_id=bk_app.tenant_id,
            daemon_token="test-token",
            volume_mounts=[{"volume_id": str(volume.uuid), "mount_path": "/workspace/shared"}],
        )

        resp = api_client.delete(url)

        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.json()["code"] == "AGENT_SANDBOX_VOLUME_IN_USE"
        assert stub_resident_client.stat(volume.storage_path, "outputs/report.html")["exists"] is True
        volume.refresh_from_db()
        assert volume.deleted_at is None

    def test_rejects_volume_mounted_by_grantee_app(
        self, api_client: APIClient, bk_user, volume: Volume, url: str, stub_resident_client
    ) -> None:
        """被授权应用名下的沙箱挂载同样阻止删除"""
        other_app = create_app(owner_username=bk_user.username)
        volume.shared_app_codes = [other_app.code]
        volume.save(update_fields=["shared_app_codes", "updated"])
        Sandbox.objects.create(
            application=other_app,
            name="sbx-grantee",
            snapshot="python:3.11-alpine",
            target="default",
            creator="test-user",
            tenant_id=other_app.tenant_id,
            daemon_token="test-token",
            volume_mounts=[{"volume_id": str(volume.uuid), "mount_path": "/workspace/shared"}],
        )

        resp = api_client.delete(url)

        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.json()["code"] == "AGENT_SANDBOX_VOLUME_IN_USE"
        volume.refresh_from_db()
        assert volume.deleted_at is None

    def test_storage_failure_keeps_record(
        self, api_client: APIClient, volume: Volume, url: str, stub_resident_client
    ) -> None:
        """共享存储清理失败时, 记录保持未删除, 调用方可重试"""
        with mock.patch.object(
            stub_resident_client, "delete_volume", side_effect=SandboxDaemonAPIError("daemon down")
        ):
            resp = api_client.delete(url)

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.json()["code"] == "AGENT_SANDBOX_VOLUME_DELETE_FAILED"
        volume.refresh_from_db()
        assert volume.deleted_at is None

    def test_service_not_ready_maps_to_502(
        self, api_client: APIClient, volume: Volume, url: str, stub_resident_client
    ) -> None:
        """常驻 daemon 未就绪时返回 502, 记录保持未删除"""
        with mock.patch.object(stub_resident_client, "delete_volume", side_effect=SandboxServiceNotReady("down")):
            resp = api_client.delete(url)

        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
        assert resp.json()["code"] == "AGENT_SANDBOX_SERVICE_NOT_READY"
        volume.refresh_from_db()
        assert volume.deleted_at is None

    def test_second_delete_returns_404(
        self, api_client: APIClient, volume: Volume, url: str, stub_resident_client
    ) -> None:
        """已软删的卷再次删除返回 404, 不会重复清理"""
        assert api_client.delete(url).status_code == status.HTTP_204_NO_CONTENT

        resp = api_client.delete(url)

        assert resp.status_code == status.HTTP_404_NOT_FOUND
