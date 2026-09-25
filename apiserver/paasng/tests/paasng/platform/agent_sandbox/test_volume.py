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

import uuid
from collections.abc import Iterator
from typing import Any
from unittest import mock

import pytest
from django.utils import timezone

from paasng.platform.agent_sandbox.constants import VOLUME_SHARED_APP_CODES_MAX, SandboxStatus
from paasng.platform.agent_sandbox.exceptions import (
    SandboxDaemonAPIError,
    VolumeInUse,
    VolumeNotFound,
    VolumeNotMountable,
    VolumeShareLimitExceeded,
)
from paasng.platform.agent_sandbox.models import Sandbox, Volume, VolumeArtifact
from paasng.platform.agent_sandbox.volume import (
    delete_volume,
    resolve_volume_mounts,
    share_volume,
    unshare_volume,
    volume_in_use,
)
from tests.paasng.platform.agent_sandbox.stubs import StubResidentDaemonClient
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def volume(bk_app: Any) -> Volume:
    """Create a Volume owned by bk_app.

    :param bk_app: The owning application fixture.
    :returns: A Volume model instance without any grant.
    """
    return Volume.objects.create(
        application=bk_app,
        name=f"vol-{uuid.uuid4().hex[:8]}",
        tenant_id=bk_app.tenant_id,
    )


def _missing_volume_id(bk_app: Any, bk_user) -> uuid.UUID:
    return uuid.uuid4()


def _soft_deleted_volume_id(bk_app: Any, bk_user) -> uuid.UUID:
    volume = Volume.objects.create(
        application=bk_app,
        name="deleted-vol",
        tenant_id=bk_app.tenant_id,
        deleted_at=timezone.now(),
    )
    return volume.uuid


def _cross_tenant_volume_id(bk_app: Any, bk_user) -> uuid.UUID:
    """即使已授权，属于其他租户的 Volume 也不可见。"""
    other_app = create_app(owner_username=bk_user.username)
    volume = Volume.objects.create(
        application=other_app,
        name="other-tenant-vol",
        tenant_id="other-tenant",
        shared_app_codes=[bk_app.code],
    )
    return volume.uuid


class TestResolveVolumeMounts:
    @pytest.fixture(autouse=True)
    def _enable_volume_feature(self, settings) -> None:
        """共享卷特性默认关闭，解析挂载项前需先打开开关。"""
        settings.AGENT_SANDBOX_VOLUME_ENABLED = True

    def test_resolves_owned_volumes_in_request_order(self, bk_app: Any) -> None:
        """每条请求按序解析为携带 CFS subPath 的挂载项。"""
        vol1 = Volume.objects.create(application=bk_app, name="vol-1", tenant_id=bk_app.tenant_id)
        vol2 = Volume.objects.create(application=bk_app, name="vol-2", tenant_id=bk_app.tenant_id)

        mounts = resolve_volume_mounts(
            bk_app,
            [
                {"volume_id": vol2.uuid, "mount_path": "/opt/data"},
                {"volume_id": vol1.uuid, "mount_path": "/workspace/shared"},
            ],
        )

        assert [m.volume_id for m in mounts] == [str(vol2.uuid), str(vol1.uuid)]
        assert mounts[0].mount_path == "/opt/data"
        assert mounts[0].sub_path == f"app/{vol2.uuid.hex}"
        assert mounts[0].read_only is False

    @pytest.mark.parametrize(
        "make_volume_id",
        [
            pytest.param(_missing_volume_id, id="missing"),
            pytest.param(_soft_deleted_volume_id, id="soft-deleted"),
            pytest.param(_cross_tenant_volume_id, id="cross-tenant"),
        ],
    )
    def test_rejects_invisible_volume(self, bk_app: Any, bk_user, make_volume_id) -> None:
        """不在本租户存活集合内的 Volume 与不存在等同。"""
        volume_id = make_volume_id(bk_app, bk_user)

        with pytest.raises(VolumeNotFound):
            resolve_volume_mounts(bk_app, [{"volume_id": volume_id, "mount_path": "/workspace/shared"}])

    def test_cross_app_volume_requires_grant(self, bk_app: Any, bk_user) -> None:
        """他人的 Volume 需先获授权才可挂载。"""
        other_app = create_app(owner_username=bk_user.username)
        volume = Volume.objects.create(
            application=other_app,
            name="cross-app-vol",
            tenant_id=bk_app.tenant_id,
        )
        requests = [{"volume_id": volume.uuid, "mount_path": "/workspace/shared"}]

        with pytest.raises(VolumeNotMountable):
            resolve_volume_mounts(bk_app, requests)

        share_volume(volume, bk_app.code)
        mounts = resolve_volume_mounts(bk_app, requests)
        assert [m.volume_id for m in mounts] == [str(volume.uuid)]


class TestShareVolume:
    def test_grant_is_idempotent(self, bk_user, volume: Volume) -> None:
        """Granting the same application twice writes it only once."""
        other_app = create_app(owner_username=bk_user.username)

        share_volume(volume, other_app.code)
        share_volume(volume, other_app.code)

        volume.refresh_from_db()
        assert volume.shared_app_codes == [other_app.code]
        assert volume.allows_mount_by(other_app)

    def test_rejects_new_grant_when_limit_reached(self, bk_user, volume: Volume) -> None:
        """New grants stop at the soft cap, while re-granting an existing code still succeeds."""
        other_app = create_app(owner_username=bk_user.username)
        volume.shared_app_codes = [f"app-{i:02d}" for i in range(VOLUME_SHARED_APP_CODES_MAX)]
        volume.save(update_fields=["shared_app_codes", "updated"])

        with pytest.raises(VolumeShareLimitExceeded):
            share_volume(volume, other_app.code)

        # 已在列表内的应用不占用新的名额，满额时重复授权仍是 no-op
        volume.shared_app_codes = [*volume.shared_app_codes[:-1], other_app.code]
        volume.save(update_fields=["shared_app_codes", "updated"])
        share_volume(volume, other_app.code)

        volume.refresh_from_db()
        assert volume.shared_app_codes.count(other_app.code) == 1
        assert len(volume.shared_app_codes) == VOLUME_SHARED_APP_CODES_MAX


class TestUnshareVolume:
    def test_revoke_is_idempotent(self, bk_user, volume: Volume) -> None:
        """Revoking removes only the given code, and revoking twice is harmless."""
        other_app = create_app(owner_username=bk_user.username)
        volume.shared_app_codes = [other_app.code, "app-kept"]
        volume.save(update_fields=["shared_app_codes", "updated"])

        unshare_volume(volume, other_app.code)
        unshare_volume(volume, other_app.code)

        volume.refresh_from_db()
        assert volume.shared_app_codes == ["app-kept"]
        assert not volume.allows_mount_by(other_app)


def _create_sandbox(
    bk_app: Any, *, volume: Volume | None = None, status: str = SandboxStatus.PENDING.value
) -> Sandbox:
    """Create a Sandbox record mounting a volume, without provisioning any resource.

    :param bk_app: The application owning the sandbox.
    :param volume: The volume to mount, omitted for sandboxes without shared mounts.
    :param status: The status persisted on the record.
    :returns: The persisted Sandbox instance.
    """
    return Sandbox.objects.create(
        application=bk_app,
        name=f"sbx-{uuid.uuid4().hex[:8]}",
        snapshot="python:3.11-alpine",
        target="default",
        status=status,
        creator="test-user",
        tenant_id=bk_app.tenant_id,
        daemon_token="test-token",
        volume_mounts=[{"volume_id": str(volume.uuid), "mount_path": "/workspace/shared"}] if volume else [],
    )


class TestVolumeInUse:
    def test_mounting_sandbox_marks_volume_in_use(self, bk_app: Any, volume: Volume) -> None:
        _create_sandbox(bk_app, volume=volume)
        assert volume_in_use(volume)

    def test_sandbox_without_mounts_does_not_block(self, bk_app: Any, volume: Volume) -> None:
        _create_sandbox(bk_app)
        assert not volume_in_use(volume)

    def test_soft_deleted_sandbox_does_not_block(self, bk_app: Any, volume: Volume) -> None:
        sandbox = _create_sandbox(bk_app, volume=volume)
        sandbox.deleted_at = timezone.now()
        sandbox.save(update_fields=["deleted_at", "updated"])
        assert not volume_in_use(volume)

    def test_err_creating_sandbox_does_not_block(self, bk_app: Any, volume: Volume) -> None:
        """创建失败的沙箱, 其工作负载已被清理, 不再持有挂载"""
        _create_sandbox(bk_app, volume=volume, status=SandboxStatus.ERR_CREATING.value)
        assert not volume_in_use(volume)

    def test_shared_volume_mounted_by_grantee_app_is_in_use(self, bk_app: Any, bk_user, volume: Volume) -> None:
        """被授权应用名下的沙箱挂载同样算占用, 不能按归属应用过滤"""
        other_app = create_app(owner_username=bk_user.username)
        volume.shared_app_codes = [other_app.code]
        volume.save(update_fields=["shared_app_codes", "updated"])
        _create_sandbox(other_app, volume=volume)

        assert volume_in_use(volume)


class TestDeleteVolume:
    @pytest.fixture()
    def stub_resident_client(self) -> Iterator[StubResidentDaemonClient]:
        client = StubResidentDaemonClient()
        with mock.patch("paasng.platform.agent_sandbox.volume.get_resident_daemon_client", return_value=client):
            yield client

    def test_wipes_storage_then_soft_deletes(self, volume: Volume, stub_resident_client) -> None:
        stub_resident_client.put_file(volume.storage_path, "outputs/report.html", b"<html></html>")

        delete_volume(volume)

        assert stub_resident_client.stat(volume.storage_path, "outputs/report.html")["exists"] is False
        volume.refresh_from_db()
        assert volume.deleted_at is not None

    def test_is_idempotent_for_a_volume_never_mounted(self, volume: Volume, stub_resident_client) -> None:
        """从未被挂载过的 Volume 在共享存储上没有目录, 删除同样应当成功"""
        delete_volume(volume)

        volume.refresh_from_db()
        assert volume.deleted_at is not None

    def test_refuses_while_a_live_sandbox_mounts_it(self, bk_app: Any, volume: Volume, stub_resident_client) -> None:
        """占用校验先于物理清理: 拒绝删除时共享存储上的数据必须原样保留"""
        stub_resident_client.put_file(volume.storage_path, "outputs/report.html", b"<html></html>")
        _create_sandbox(bk_app, volume=volume)

        with (
            mock.patch.object(stub_resident_client, "delete_volume") as delete_volume_spy,
            pytest.raises(VolumeInUse),
        ):
            delete_volume(volume)

        delete_volume_spy.assert_not_called()
        assert stub_resident_client.stat(volume.storage_path, "outputs/report.html")["exists"] is True
        volume.refresh_from_db()
        assert volume.deleted_at is None

    def test_keeps_record_when_daemon_fails(self, volume: Volume, stub_resident_client) -> None:
        """存储清理失败时不得软删记录, 否则用户没有任何入口重试"""
        with (
            mock.patch.object(stub_resident_client, "delete_volume", side_effect=SandboxDaemonAPIError("boom")),
            pytest.raises(SandboxDaemonAPIError),
        ):
            delete_volume(volume)

        volume.refresh_from_db()
        assert volume.deleted_at is None

    def test_removes_archived_objects(self, volume: Volume, stub_resident_client) -> None:
        VolumeArtifact.objects.create(
            volume=volume,
            rel_path="outputs/report.html",
            mtime="2026-06-24T10:00:00Z",
            size=13,
            sha256="0" * 64,
            bkrepo_key="pv-archives/app-demo/report.html",
            archived_at=timezone.now(),
            tenant_id=volume.tenant_id,
        )

        with mock.patch("paasng.platform.agent_sandbox.artifact.make_blob_store") as make_blob_store:
            delete_volume(volume)

        make_blob_store.return_value.delete_file.assert_called_once_with("pv-archives/app-demo/report.html")
        assert VolumeArtifact.objects.filter(volume=volume).count() == 0
        volume.refresh_from_db()
        assert volume.deleted_at is not None

    def test_archive_cleanup_failure_does_not_block(self, volume: Volume, stub_resident_client) -> None:
        """bkrepo 故障不应阻塞卷删除"""
        with mock.patch(
            "paasng.platform.agent_sandbox.artifact.make_blob_store", side_effect=RuntimeError("bkrepo down")
        ):
            delete_volume(volume)

        volume.refresh_from_db()
        assert volume.deleted_at is not None

    def test_archive_cleanup_exception_does_not_block(self, volume: Volume, stub_resident_client) -> None:
        """归档清理本身抛异常时也不得阻塞卷删除"""
        with mock.patch(
            "paasng.platform.agent_sandbox.volume.delete_volume_artifacts", side_effect=RuntimeError("boom")
        ):
            delete_volume(volume)

        volume.refresh_from_db()
        assert volume.deleted_at is not None
