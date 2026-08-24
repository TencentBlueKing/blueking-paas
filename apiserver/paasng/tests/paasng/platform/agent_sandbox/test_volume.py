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

from paasng.platform.agent_sandbox.constants import VOLUME_SHARED_APP_CODES_MAX
from paasng.platform.agent_sandbox.exceptions import VolumeShareLimitExceeded
from paasng.platform.agent_sandbox.models import Volume
from paasng.platform.agent_sandbox.volume import share_volume, unshare_volume
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
