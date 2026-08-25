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

from paasng.platform.agent_sandbox.models import Volume
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
        self, api_client: APIClient, bk_app: Any, bk_user, url_name: str, method: str, payload: dict | None
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
