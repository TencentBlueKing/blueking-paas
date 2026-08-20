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

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from paasng.platform.agent_sandbox.constants import VOLUME_SHARED_APP_CODES_MAX
from paasng.platform.agent_sandbox.models import Volume
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.usefixtures("_mock_verified_app_permission")
class TestVolumeViewSetOwnership:
    """Delete still requires the path app to own the Volume."""

    def test_delete_other_app_volume_returns_404(self, api_client: APIClient, bk_app: Any, bk_user) -> None:
        """Knowing another app's volume UUID is not enough to delete it."""
        other_app = create_app(owner_username=bk_user.username)
        other_volume = Volume.objects.create(
            application=other_app,
            name="other-vol",
            tenant_id=bk_app.tenant_id,
        )

        url = reverse(
            "agent_sandbox.volume.destroy",
            kwargs={"code": bk_app.code, "volume_id": other_volume.uuid},
        )
        resp = api_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        other_volume.refresh_from_db()
        assert other_volume.deleted_at is None


@pytest.mark.usefixtures("_mock_verified_app_permission")
class TestVolumeShareAPI:
    """Owner grants/revokes mount access; list still only returns owned Volumes."""

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
        assert other_app.code in (volume.shared_app_codes or [])

        # idempotent grant
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
        assert other_app.code not in (volume.shared_app_codes or [])

    def test_share_self_is_noop_unknown_rejected(self, api_client: APIClient, bk_app: Any, volume: Volume) -> None:
        """Self-grant is a no-op; unknown grantee still returns APP_NOT_FOUND."""
        shares_url = reverse(
            "agent_sandbox.volume.shares",
            kwargs={"code": bk_app.code, "volume_id": volume.uuid},
        )
        resp = api_client.post(shares_url, data={"grantee_app_code": bk_app.code}, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        volume.refresh_from_db()
        assert volume.shared_app_codes == []

        resp = api_client.post(shares_url, data={"grantee_app_code": "no-such-app"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

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

    def test_share_rejects_when_limit_reached(
        self, api_client: APIClient, bk_app: Any, bk_user, volume: Volume
    ) -> None:
        """New grants are rejected once shared_app_codes hits the soft cap; re-grant is still idempotent."""
        other_app = create_app(owner_username=bk_user.username)
        volume.shared_app_codes = [f"app-{i:02d}" for i in range(VOLUME_SHARED_APP_CODES_MAX)]
        volume.save(update_fields=["shared_app_codes", "updated"])

        shares_url = reverse(
            "agent_sandbox.volume.shares",
            kwargs={"code": bk_app.code, "volume_id": volume.uuid},
        )
        resp = api_client.post(shares_url, data={"grantee_app_code": other_app.code}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        volume.refresh_from_db()
        assert other_app.code not in volume.shared_app_codes
        assert len(volume.shared_app_codes) == VOLUME_SHARED_APP_CODES_MAX

        volume.shared_app_codes = volume.shared_app_codes[:-1] + [other_app.code]
        volume.save(update_fields=["shared_app_codes", "updated"])
        resp = api_client.post(shares_url, data={"grantee_app_code": other_app.code}, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        volume.refresh_from_db()
        assert volume.shared_app_codes.count(other_app.code) == 1
        assert len(volume.shared_app_codes) == VOLUME_SHARED_APP_CODES_MAX

    def test_share_other_app_volume_returns_404(self, api_client: APIClient, bk_app: Any, bk_user) -> None:
        """Only the owner can grant access to a Volume."""
        other_app = create_app(owner_username=bk_user.username)
        other_volume = Volume.objects.create(
            application=other_app,
            name="other-vol",
            tenant_id=bk_app.tenant_id,
        )
        shares_url = reverse(
            "agent_sandbox.volume.shares",
            kwargs={"code": bk_app.code, "volume_id": other_volume.uuid},
        )
        resp = api_client.post(shares_url, data={"grantee_app_code": other_app.code}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
