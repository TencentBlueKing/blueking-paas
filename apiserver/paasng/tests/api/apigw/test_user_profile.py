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

import pytest
from django.test.utils import override_settings
from rest_framework import status

from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import UserProfile

pytestmark = pytest.mark.django_db

USER_PROFILE_URL = "/api/accounts/user_profile/"


class TestRegisterUserProfile:
    """用户态注册 UserProfile 接口测试"""

    def test_register_new_user(self, api_client, bk_user):
        """没有 UserProfile 的用户调用后建档为普通用户。"""
        assert not UserProfile.objects.filter(user=bk_user.pk).exists()

        resp = api_client.post(USER_PROFILE_URL)

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        assert resp.json() == {
            "username": bk_user.username,
            "tenant_id": DEFAULT_TENANT_ID,
            "role": SiteRole.USER.value,
        }
        assert UserProfile.objects.get(user=bk_user.pk).role == SiteRole.USER.value

    def test_existing_profile_unchanged(self, api_client, bk_user):
        """已注册的用户重复调用不改动已有角色与租户。"""
        UserProfile.objects.create(user=bk_user.pk, tenant_id=DEFAULT_TENANT_ID, role=SiteRole.ADMIN.value)

        resp = api_client.post(USER_PROFILE_URL)
        resp_again = api_client.post(USER_PROFILE_URL)

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        assert resp.json()["role"] == SiteRole.ADMIN.value
        assert resp_again.json() == resp.json()
        assert UserProfile.objects.filter(user=bk_user.pk).count() == 1

    @override_settings(AUTO_CREATE_REGULAR_USER=False)
    def test_auto_create_disabled(self, api_client, bk_user):
        """平台关闭自助注册时拒绝，且不建档。"""
        resp = api_client.post(USER_PROFILE_URL)

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "USER_PROFILE_AUTO_CREATE_DISABLED"
        assert not UserProfile.objects.filter(user=bk_user.pk).exists()
