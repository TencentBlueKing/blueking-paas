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

from paasng.infras.accounts.constants import AccountFeatureFlag as FeatureFlag
from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import AccountFeatureFlag, UserProfile
from paasng.infras.sysapi_client.constants import ClientRole
from paasng.infras.sysapi_client.models import AuthenticatedAppAsClient, SysAPIClient
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


class TestPlatformManagerViewSet:
    """平台管理员 API 测试"""

    def test_list_manager(self, plat_mgt_api_client):
        """测试获取平台管理员列表"""
        bulk_url = reverse("plat_mgt.users.user_profiles.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_bulk_create_manager(self, plat_mgt_api_client):
        """测试批量创建平台管理员"""
        bulk_url = reverse("plat_mgt.users.user_profiles.bulk")
        users = [f"test_user_{generate_random_string(6)}" for _ in range(2)]
        user_ids = [user_id_encoder.encode(settings.USER_TYPE, user) for user in users]

        # 首先为测试用户创建 UserProfile 记录，因为视图实现要求用户已登录过平台
        for user_id in user_ids:
            UserProfile.objects.create(user=user_id, role=SiteRole.USER.value)

        data = {"users": users}
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        # 验证用户角色已更新为管理员
        for user_id in user_ids:
            profile = UserProfile.objects.get(user=user_id)
            assert profile.role == SiteRole.ADMIN.value

    def test_bulk_create_manager_nonexistent_users(self, plat_mgt_api_client):
        """测试批量创建平台管理员 - 处理未登录用户的情况"""
        bulk_url = reverse("plat_mgt.users.user_profiles.bulk")
        users = [f"nonexistent_user_{generate_random_string(6)}" for _ in range(2)]

        data = {"users": users}
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")

        # 应当返回 400 错误，因为这些用户未登录过平台
        assert rsp.status_code == status.HTTP_400_BAD_REQUEST
        assert "has not logged in to the platform yet" in rsp.data["detail"]

    def test_destroy_manager(self, plat_mgt_api_client):
        """测试删除平台管理员"""
        # 先创建用户配置文件
        user = f"test_admin_{generate_random_string(6)}"
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)
        # 直接创建一个管理员角色的用户配置
        UserProfile.objects.create(user=user_id, role=SiteRole.ADMIN.value)

        # 确认该管理员已存在
        profile = UserProfile.objects.get(user=user_id)
        assert profile.role == SiteRole.ADMIN.value

        # 尝试删除这个管理员
        delete_url = reverse("plat_mgt.users.user_profiles.delete", kwargs={"user": user})
        delete_rsp = plat_mgt_api_client.delete(delete_url)
        assert delete_rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证管理员角色已被更改为普通用户，而不是删除
        profile.refresh_from_db()
        assert profile.role == SiteRole.USER.value


class TestAccountFeatureFlagManageViewSet:
    def test_list_feature_flags(self, plat_mgt_api_client):
        """测试获取用户特性列表"""
        bulk_url = reverse("plat_mgt.users.account_feature_flags.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_upsert_feature_flags(self, plat_mgt_api_client):
        """测试创建或更新用户特性"""
        bulk_url = reverse("plat_mgt.users.account_feature_flags.bulk")
        user = f"test_user_{generate_random_string(6)}"
        feature = FeatureFlag.ALLOW_ADVANCED_CREATION_OPTIONS.value
        data = {"user": user, "feature": feature, "is_effect": "true"}

        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        # 验证已在数据库写入
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)
        assert AccountFeatureFlag.objects.filter(user=user_id, name=feature, effect=True).exists()

    def test_destroy_feature_flags(self, plat_mgt_api_client):
        """测试删除用户特性"""
        user = f"test_user_{generate_random_string(6)}"
        feature = FeatureFlag.ALLOW_ADVANCED_CREATION_OPTIONS.value

        # 创建用户特性
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)
        AccountFeatureFlag.objects.create(
            user=user_id,
            name=feature,
            effect=True,
        )

        # 验证已在数据库写入
        exist_feature_flag = AccountFeatureFlag.objects.filter(user=user_id, name=feature, effect=True).first()
        assert exist_feature_flag

        # 删除特性
        delete_url = reverse(
            "plat_mgt.users.account_feature_flags.delete",
            kwargs={"id": exist_feature_flag.id},
        )
        delete_rsp = plat_mgt_api_client.delete(delete_url)
        assert delete_rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证已被删除
        assert not AccountFeatureFlag.objects.filter(user=user_id, name=feature).exists()


class TestSystemAPIUserViewSet:
    def test_list_system_api_users(self, plat_mgt_api_client):
        """测试获取系统 API 用户列表"""
        bulk_url = reverse("plat_mgt.users.system_api_user.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_create_system_api_users(self, plat_mgt_api_client):
        """测试创建系统 API 用户"""
        bulk_url = reverse("plat_mgt.users.system_api_user.bulk")
        bk_app_code = f"{generate_random_string(6)}"
        user = f"authed-app-{bk_app_code}"
        role = ClientRole.BASIC_READER.value
        data = {"bk_app_code": bk_app_code, "role": role}

        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        sys_api_client = SysAPIClient.objects.filter(name=user, role=50).first()
        assert sys_api_client
        assert AuthenticatedAppAsClient.objects.filter(client=sys_api_client).exists()

    def test_update_system_api_users(self, plat_mgt_api_client):
        """测试更新系统 API 用户"""
        bulk_url = reverse("plat_mgt.users.system_api_user.bulk")
        bk_app_code = f"{generate_random_string(6)}"
        user = f"authed-app-{bk_app_code}"
        role = ClientRole.BASIC_READER.value
        data = {"bk_app_code": bk_app_code, "role": role}

        # 先创建一个系统 API 用户
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        new_role = ClientRole.BASIC_MAINTAINER.value
        data = {"bk_app_code": bk_app_code, "role": new_role}
        rsp = plat_mgt_api_client.put(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证数据库中的角色已更新
        sys_api_client = SysAPIClient.objects.get(name=user)
        assert sys_api_client.role == new_role

    def test_destroy_system_api_users(self, plat_mgt_api_client):
        """测试删除系统 API 用户"""
        # 先创建一个系统 API 用户
        bulk_url = reverse("plat_mgt.users.system_api_user.bulk")
        bk_app_code = f"{generate_random_string(6)}"
        user = f"authed-app-{bk_app_code}"
        role = ClientRole.BASIC_READER.value
        data = {"user": user, "bk_app_code": bk_app_code, "role": role}

        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        # 验证已在数据库写入
        assert SysAPIClient.objects.filter(name=user, role=role, is_active=True).exists()

        # 删除该用户
        delete_url = reverse(
            "plat_mgt.users.system_api_user.delete",
            kwargs={"user": user},
        )
        delete_rsp = plat_mgt_api_client.delete(delete_url)
        assert delete_rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证已被删除
        assert not SysAPIClient.objects.filter(name=user, is_active=True).exists()
