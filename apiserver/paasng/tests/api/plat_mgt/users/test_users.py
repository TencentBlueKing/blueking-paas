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
        bulk_url = reverse("plat_mgt.users.admin_user.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_bulk_create_manager(self, plat_mgt_api_client):
        """测试批量创建平台管理员"""
        bulk_url = reverse("plat_mgt.users.admin_user.bulk")
        users = [f"test_user_{generate_random_string(6)}" for _ in range(2)]
        user_ids = [user_id_encoder.encode(settings.USER_TYPE, user) for user in users]

        data = [{"user": users[0], "tenant_id": "default"}, {"user": users[1], "tenant_id": "default"}]
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        # 验证用户角色已创建且为管理员, 租户为给定租户
        for user_id in user_ids:
            profile = UserProfile.objects.get(user=user_id)
            assert profile.role == SiteRole.ADMIN.value
            assert profile.tenant_id == "default"

        # 尝试再次添加同一批用户作为管理员
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_400_BAD_REQUEST
        assert "already administrators" in rsp.data["detail"]

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
        delete_url = reverse("plat_mgt.users.admin_user.delete", kwargs={"user": user})
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

        # 尝试再次添加同一特性
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_400_BAD_REQUEST
        assert f"{user} already has {feature} feature" in rsp.data["detail"]

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

    def test_list_features(self, plat_mgt_api_client):
        """测试获取用户特性种类列表"""
        list_url = reverse("plat_mgt.users.account_features.feature_list")
        rsp = plat_mgt_api_client.get(list_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

        # 验证返回的数据格式
        for item in rsp.data:
            assert "value" in item
            assert "label" in item


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
        name = f"authed-app-{bk_app_code}"
        role = ClientRole.BASIC_READER.value
        data = {"name": name, "bk_app_code": bk_app_code, "role": role}

        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        # 验证已在数据库写入
        assert SysAPIClient.objects.filter(name=name, role=role, is_active=True).exists()

        # 删除该用户
        delete_url = reverse(
            "plat_mgt.users.system_api_user.delete",
            kwargs={"name": name},
        )
        delete_rsp = plat_mgt_api_client.delete(delete_url)
        assert delete_rsp.status_code == status.HTTP_204_NO_CONTENT

        # 验证已被删除
        assert not SysAPIClient.objects.filter(name=name, is_active=True).exists()

    def test_list_system_api_roles(self, plat_mgt_api_client):
        """测试获取系统 API 权限种类列表"""
        list_url = reverse("plat_mgt.users.system_api_roles.role_list")
        rsp = plat_mgt_api_client.get(list_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

        # 验证返回的数据格式
        for item in rsp.data:
            assert "value" in item
            assert "label" in item
