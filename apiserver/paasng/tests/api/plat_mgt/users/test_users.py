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
from paasng.platform.applications.models import Application
from tests.utils.helpers import generate_random_string, override_settings

pytestmark = pytest.mark.django_db


class TestPlatformManagerViewSet:
    """平台管理员 API 测试"""

    def test_list_manager(self, plat_mgt_api_client):
        """测试获取平台管理员列表"""
        bulk_url = reverse("plat_mgt.users.admin_user.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_bulk_create_manager_single_tenant(self, plat_mgt_api_client):
        """测试单租户模式下批量创建平台管理员"""
        bulk_url = reverse("plat_mgt.users.admin_user.bulk")
        with override_settings(ENABLE_MULTI_TENANT_MODE=False):
            users = [f"test_user_{generate_random_string(6)}" for _ in range(3)]
            user_ids = [user_id_encoder.encode(settings.USER_TYPE, user) for user in users]
            data = [
                {"user": users[0], "tenant_id": "non-default"},
                {"user": users[1], "tenant_id": None},
                {"user": users[2]},
            ]
            rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
            assert rsp.status_code == status.HTTP_201_CREATED

            for user_id in user_ids:
                profile = UserProfile.objects.get(user=user_id)
                assert profile.role == SiteRole.ADMIN.value
                assert profile.tenant_id == "default"

    def test_bulk_create_manager_multi_tenant(self, plat_mgt_api_client):
        """测试多租户模式下批量创建平台管理员"""
        bulk_url = reverse("plat_mgt.users.admin_user.bulk")
        with override_settings(ENABLE_MULTI_TENANT_MODE=True):
            # 测试租户 ID 为 None 或缺失的情况
            users = [f"test_user_{generate_random_string(6)}" for _ in range(2)]
            data = [{"user": users[0]}, {"user": users[1], "tenant_id": None}]
            rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
            assert rsp.status_code == status.HTTP_400_BAD_REQUEST
            assert "VALIDATION_ERROR" in rsp.data["code"]

            # 测试租户 ID 为有效值的情况
            users = [f"test_user_{generate_random_string(6)}" for _ in range(2)]
            user_ids = [user_id_encoder.encode(settings.USER_TYPE, user) for user in users]
            tenant_id = "non-default"
            data = [{"user": users[0], "tenant_id": tenant_id}, {"user": users[1], "tenant_id": tenant_id}]
            rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
            assert rsp.status_code == status.HTTP_201_CREATED

            for user_id in user_ids:
                profile = UserProfile.objects.get(user=user_id)
                assert profile.role == SiteRole.ADMIN.value
                assert profile.tenant_id == tenant_id

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
        assert rsp.data["code"] == "USER_FEATURE_FLAG_ALREADY_EXISTS"

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
            assert "default_flag" in item


class TestSystemAPIClientViewSet:
    def test_list_system_api_users(self, plat_mgt_api_client):
        """测试获取已授权应用列表"""
        bulk_url = reverse("plat_mgt.users.sysapi_client.bulk")
        rsp = plat_mgt_api_client.get(bulk_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

    def test_create_system_api_clients(self, plat_mgt_api_client):
        """测试创建已授权应用"""
        bulk_url = reverse("plat_mgt.users.sysapi_client.bulk")

        # 创建一个有效的应用
        app_code = f"test_app_{generate_random_string(6)}"
        Application.objects.create(code=app_code, name=app_code)

        # 校验是否成功创建新已验证应用
        role = ClientRole.BASIC_READER.value
        data = {"bk_app_code": app_code, "role": role}
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        client_name = f"authed-app-{app_code}"
        client = SysAPIClient.objects.get(name=client_name)
        assert client.role == role
        assert client.is_active is True

        auth_relation = AuthenticatedAppAsClient.objects.get(client=client)
        assert auth_relation.bk_app_code == app_code

        # 尝试为已认证的应用再次创建客户端 (预期失败)
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_400_BAD_REQUEST
        assert rsp.data["code"] == "APP_AUTHENTICATED_ALREADY_EXISTS"

        # 删除认证关系并将客户端设为非活动状态
        auth_relation.delete()
        client.is_active = False
        client.save()

        # 测试重新激活一个非活动的客户端
        rsp = plat_mgt_api_client.post(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_201_CREATED

        client.refresh_from_db()
        assert client.is_active is True
        assert client.role == role
        assert AuthenticatedAppAsClient.objects.filter(client=client, bk_app_code=app_code).exists()

    def test_update_system_api_clients(self, plat_mgt_api_client):
        """测试更新已授权应用"""
        bulk_url = reverse("plat_mgt.users.sysapi_client.bulk")
        app_code = f"{generate_random_string(6)}"

        # 创建一个有效的已授权应用
        Application.objects.create(code=app_code, name=app_code)
        client_name = f"authed-app-{app_code}"
        init_role = ClientRole.BASIC_READER.value
        client = SysAPIClient.objects.create(name=client_name, role=init_role, is_active=True)
        auth_app_client = AuthenticatedAppAsClient.objects.create(client=client, bk_app_code=app_code)

        # 测试更新为不同的角色
        new_role = ClientRole.BASIC_MAINTAINER.value
        data = {"bk_app_code": app_code, "role": new_role}
        rsp = plat_mgt_api_client.put(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_204_NO_CONTENT
        client.refresh_from_db()
        assert client.role == new_role

        # 测试更新不存在的客户端
        non_existent_app = f"non_existent_app_{generate_random_string(6)}"
        data = {"bk_app_code": non_existent_app, "role": new_role}
        rsp = plat_mgt_api_client.put(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_400_BAD_REQUEST
        assert rsp.data["code"] == "SYSAPI_CLIENT_NOT_FOUND"

        # 测试更新已禁用的客户端
        client.is_active = False
        client.save()
        auth_app_client.delete()
        data = {"bk_app_code": app_code, "role": new_role}
        rsp = plat_mgt_api_client.put(bulk_url, data, format="json")
        assert rsp.status_code == status.HTTP_400_BAD_REQUEST
        assert rsp.data["code"] == "SYSAPI_CLIENT_NOT_FOUND"

    def test_destroy_system_api_clients(self, plat_mgt_api_client):
        """测试删除已授权应用"""
        app_code = f"{generate_random_string(6)}"
        client_name = f"authed-app-{app_code}"
        # 先创建一个已授权应用
        Application.objects.create(code=app_code, name=app_code)
        client_name = f"authed-app-{app_code}"
        init_role = ClientRole.BASIC_READER.value
        client = SysAPIClient.objects.create(name=client_name, role=init_role, is_active=True)
        AuthenticatedAppAsClient.objects.create(client=client, bk_app_code=app_code)

        delete_url = reverse("plat_mgt.users.sysapi_client.delete", kwargs={"name": app_code})
        rsp = plat_mgt_api_client.delete(delete_url)
        assert rsp.status_code == status.HTTP_204_NO_CONTENT
        # 验证已被删除
        client.refresh_from_db()
        assert not client.is_active
        # 认证关系应该已经删除
        assert not AuthenticatedAppAsClient.objects.filter(client=client, bk_app_code=app_code).exists()

    def test_list_system_api_roles(self, plat_mgt_api_client):
        """测试获取授权应用的权限种类列表"""
        list_url = reverse("plat_mgt.users.sysapi_client.role_list")
        rsp = plat_mgt_api_client.get(list_url)
        assert rsp.status_code == status.HTTP_200_OK
        assert isinstance(rsp.data, list)

        # 验证返回的数据格式
        for item in rsp.data:
            assert "value" in item
            assert "label" in item
