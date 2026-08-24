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
from typing import Any

import pytest
from django.utils import timezone

from paasng.platform.agent_sandbox.constants import VOLUME_SHARED_APP_CODES_MAX
from paasng.platform.agent_sandbox.exceptions import VolumeNotFound, VolumeNotMountable, VolumeShareLimitExceeded
from paasng.platform.agent_sandbox.models import Volume
from paasng.platform.agent_sandbox.volume import resolve_volume_mounts, share_volume, unshare_volume
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
