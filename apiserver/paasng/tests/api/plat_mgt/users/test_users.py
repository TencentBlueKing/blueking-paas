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

import pytest
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.urls import reverse
from rest_framework import status

from paasng.infras.accounts.models import AccountFeatureFlag, UserProfile
from paasng.infras.sysapi_client.models import ClientPrivateToken, SysAPIClient
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


class TestPlatMgtAdminViewSet:
    """平台管理员 API 测试"""

    def test_list_admins(self, plat_mgt_api_client):
        """测试获取平台管理员列表"""
        bulk_url = reverse("plat_mgt.users.userprofiles.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_bulk_create_admins(self, plat_mgt_api_client):
        """测试批量创建平台管理员"""
        bulk_url = reverse("plat_mgt.users.userprofiles.bulk")
        users = [f"test_user_{generate_random_string(6)}" for _ in range(2)]
        data = {"user_list": users}

        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_200_OK

        # 验证创建的管理员在响应中
        created_users = [admin["user"] for admin in rsp.data]
        for username in users:
            assert username in created_users

    def test_destroy_admin(self, plat_mgt_api_client):
        """测试删除平台管理员"""

        # 先通过API创建一个测试管理员，而不是直接使用模型
        # 创建管理员
        bulk_url = reverse("plat_mgt.users.userprofiles.bulk")
        user = f"test_admin_{generate_random_string(6)}"
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)

        # 使用API创建管理员
        create_data = {"user_list": [user]}
        create_response = plat_mgt_api_client.post(bulk_url, create_data, format="json")
        assert create_response.status_code == status.HTTP_200_OK

        # 确认该管理员已被成功创建
        admin_list = plat_mgt_api_client.get(bulk_url).data
        assert user in [item["user"] for item in admin_list]

        # 现在尝试删除这个管理员
        delete_url = reverse("plat_mgt.users.userprofiles.delete", kwargs={"user": user})
        delete_rsp = plat_mgt_api_client.delete(delete_url)
        assert delete_rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证管理员已被删除
        assert not UserProfile.objects.filter(user=user_id).exists()


class TestAccountFeatureFlagManageViewSet:
    def test_list_feature_flags(self, plat_mgt_api_client):
        """测试获取用户特性列表"""
        bulk_url = reverse("plat_mgt.users.account_feature_flags.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_update_or_create_feature_flags(self, plat_mgt_api_client):
        """测试创建或更新用户特性"""
        bulk_url = reverse("plat_mgt.users.account_feature_flags.bulk")
        user = f"test_user_{generate_random_string(6)}"
        feature = "demo-feature"
        data = {"user": user, "feature": feature, "isEffect": True}

        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证已在数据库写入
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)
        assert AccountFeatureFlag.objects.filter(user=user_id, name=feature, effect=True).exists()

    def test_destroy_feature_flags(self, plat_mgt_api_client):
        """测试删除用户特性"""
        url_update = reverse("plat_mgt.users.account_feature_flags.bulk")
        user = f"test_user_{generate_random_string(6)}"
        feature = "remove-this-feature"
        data = {"user": user, "feature": feature, "isEffect": True}

        plat_mgt_api_client.post(url_update, data, format="json")

        # 删除特性
        delete_url = reverse(
            "plat_mgt.users.account_feature_flags.delete",
            kwargs={"user": user, "feature": feature},
        )
        delete_rsp = plat_mgt_api_client.delete(delete_url)
        assert delete_rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证已被删除
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)
        assert not AccountFeatureFlag.objects.filter(user=user_id, name="remove-this-feature").exists()


class TestSystemAPIUserViewSet:
    def test_list_system_api_users(self, plat_mgt_api_client):
        """测试获取系统 API 用户列表"""
        bulk_url = reverse("plat_mgt.users.system_api_user.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_update_or_create_system_api_users(self, plat_mgt_api_client):
        """测试创建或更新系统 API 用户"""
        bulk_url = reverse("plat_mgt.users.system_api_user.bulk")
        user = f"test_sys_user_{generate_random_string(6)}"
        bk_app_code = "test_app"
        data = {"user": user, "bk_app_code": bk_app_code, "role": 50}

        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_204_NO_CONTENT

    def test_destroy_system_api_users(self, plat_mgt_api_client):
        """测试删除系统 API 用户"""
        # 先创建一个系统 API 用户
        bulk_url = reverse("plat_mgt.users.system_api_user.bulk")
        user = f"test_sys_user_{generate_random_string(6)}"
        bk_app_code = "test_app"
        data = {"user": user, "bk_app_code": bk_app_code, "role": 50}
        plat_mgt_api_client.post(bulk_url, data, format="json")

        # 删除该用户
        delete_url = reverse(
            "plat_mgt.users.system_api_user.delete",
            kwargs={"user": user, "role": 50},
        )
        delete_rsp = plat_mgt_api_client.delete(delete_url)
        assert delete_rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证已被删除
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)
        assert not SysAPIClient.objects.filter(name=user_id).exists()
        assert not ClientPrivateToken.objects.filter(client__name=user_id).exists()
