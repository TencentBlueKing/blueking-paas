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

import re
import uuid
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status

from paasng.platform.agent_sandbox.e2b.constants import MAX_ACTIVE_KEYS_PER_APP
from paasng.platform.agent_sandbox.models import E2BApiKey

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SDK_API_KEY_PATTERN = re.compile(r"\Ae2b_[0-9a-f]+\Z")


@pytest.fixture()
def _mock_e2b_verified_app():
    """绕过 APIGW 应用校验。e2b 的 key 管理接口有自己的 IsAPIGWVerifiedApp 引用。"""
    with (
        mock.patch(
            "paasng.platform.agent_sandbox.e2b.views.IsAPIGWVerifiedApp.has_permission",
            return_value=True,
        ),
        mock.patch(
            "paasng.platform.agent_sandbox.e2b.views.IsAPIGWVerifiedApp.has_object_permission",
            return_value=True,
        ),
    ):
        yield


def _list_url(app):
    return reverse("agent_sandbox.e2b.api_key", kwargs={"code": app.code})


def _detail_url(app, key_id):
    return reverse("agent_sandbox.e2b.api_key.destroy", kwargs={"code": app.code, "key_id": key_id})


@pytest.mark.usefixtures("_mock_e2b_verified_app")
class TestCreate:
    def test_returns_plaintext_once(self, api_client, bk_app):
        """响应里给出明文，库里只有摘要与前缀。"""
        resp = api_client.post(_list_url(bk_app), data={"name": "ci"})

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        plain_key = body["api_key"]
        assert SDK_API_KEY_PATTERN.match(plain_key)
        assert body["name"] == "ci"
        assert plain_key.startswith(body["key_prefix"])

        key_obj = E2BApiKey.objects.get(uuid=body["uuid"])
        assert key_obj.application == bk_app
        assert plain_key not in (key_obj.key_hash, key_obj.key_prefix)

    def test_name_is_optional(self, api_client, bk_app):
        resp = api_client.post(_list_url(bk_app), data={})

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["name"] == ""

    def test_rejects_when_quota_exhausted(self, api_client, bk_app):
        """达到上限后返回 400。"""
        for _ in range(MAX_ACTIVE_KEYS_PER_APP):
            assert api_client.post(_list_url(bk_app), data={}).status_code == status.HTTP_201_CREATED

        resp = api_client.post(_list_url(bk_app), data={})

        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.usefixtures("_mock_e2b_verified_app")
class TestList:
    def test_returns_metadata_without_plaintext(self, api_client, bk_app):
        """列表只返回前缀与元信息，不含明文。"""
        plain_key = api_client.post(_list_url(bk_app), data={"name": "ci"}).json()["api_key"]

        resp = api_client.get(_list_url(bk_app))

        assert resp.status_code == status.HTTP_200_OK
        assert plain_key not in resp.content.decode()
        (item,) = resp.json()
        assert set(item) == {"uuid", "name", "key_prefix", "created"}

    def test_scoped_to_application(self, api_client, bk_app, bk_app_full):
        api_client.post(_list_url(bk_app), data={})
        api_client.post(_list_url(bk_app_full), data={})

        assert len(api_client.get(_list_url(bk_app)).json()) == 1

    def test_revoked_key_is_hidden(self, api_client, bk_app):
        """列表与签发配额同口径：吊销后既不占名额，也不再出现在列表里。"""
        kept = api_client.post(_list_url(bk_app), data={"name": "kept"}).json()["uuid"]
        revoked = api_client.post(_list_url(bk_app), data={"name": "revoked"}).json()["uuid"]
        api_client.delete(_detail_url(bk_app, revoked))

        (item,) = api_client.get(_list_url(bk_app)).json()
        assert item["uuid"] == kept
        # 只是从列表里隐去，记录仍在库中
        assert E2BApiKey.objects.filter(uuid=revoked).exists()


@pytest.mark.usefixtures("_mock_e2b_verified_app")
class TestDestroy:
    def test_revokes_without_deleting(self, api_client, bk_app):
        key_id = api_client.post(_list_url(bk_app), data={}).json()["uuid"]

        resp = api_client.delete(_detail_url(bk_app, key_id))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        key_obj = E2BApiKey.objects.get(uuid=key_id)
        assert key_obj.enabled is False
        assert key_obj.revoked_at is not None

    def test_other_application_gets_404(self, api_client, bk_app, bk_app_full):
        """吊销不属于本应用的 key 返回 404，不区分「不存在」与「无权限」。"""
        key_id = api_client.post(_list_url(bk_app), data={}).json()["uuid"]

        resp = api_client.delete(_detail_url(bk_app_full, key_id))

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert E2BApiKey.objects.get(uuid=key_id).enabled is True

    def test_unknown_key_gets_404(self, api_client, bk_app):
        resp = api_client.delete(_detail_url(bk_app, uuid.uuid4()))

        assert resp.status_code == status.HTTP_404_NOT_FOUND
