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

import logging

from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import AccountFeatureFlag, UserProfile
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.sysapi_client.models import AuthenticatedAppAsClient, SysAPIClient
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_mgt.users.serializers import (
    AccountFeatureFlagReadSLZ,
    AccountFeatureFlagWriteSLZ,
    PlatMgtAdminReadSLZ,
    PlatMgtAdminWriteSLZ,
    SystemAPIUserReadSLZ,
    SystemAPIUserWriteSLZ,
)

logger = logging.getLogger(__name__)


class PlatMgtAdminViewSet(viewsets.GenericViewSet):
    """平台管理员相关 API"""

    # 需要平台管理权限才能访问
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request, *args, **kwargs):
        """获取平台管理员列表"""
        admin_profiles = (
            UserProfile.objects.filter(
                role__in=[SiteRole.ADMIN.value, SiteRole.SUPER_USER.value],
            )
            .order_by("-created")
            .values()
        )
        slz = PlatMgtAdminReadSLZ(admin_profiles, many=True)
        return Response(slz.data)

    @atomic
    def bulk_create(self, request, *args, **kwargs):
        """批量创建平台管理员"""
        slz = PlatMgtAdminWriteSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        role = SiteRole.ADMIN.value

        # 获取验证后的用户ID列表
        user_ids = slz.validated_data["username_list"]

        # 获取创建前的数据 - 查询数据库中已存在的用户
        existing_profiles = UserProfile.objects.filter(user__in=user_ids)
        before_data = list(PlatMgtAdminReadSLZ(existing_profiles, many=True).data)

        created_profiles = []
        for userid in slz.data["username_list"]:
            obj, _ = UserProfile.objects.update_or_create(user=userid, defaults={"role": role})
            obj.refresh_from_db()
            created_profiles.append(obj)

        # 获取创建后的数据
        results_serializer = PlatMgtAdminReadSLZ(created_profiles, many=True)
        after_data = list(results_serializer.data)

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )
        return Response(results_serializer.data)

    def destroy(self, request, userid, *args, **kwargs):
        """删除平台管理员"""
        if not userid:
            return Response({"detail": "Userid is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 获取删除前的用户信息
            before_query = UserProfile.objects.filter(user=userid)
            before_data = list(PlatMgtAdminReadSLZ(before_query, many=True).data)

            # 删除用户
            UserProfile.objects.filter(user=userid).delete()

            # 尝试获取删除后的用户信息
            after_query = UserProfile.objects.filter(user=userid)
            after_data = list(PlatMgtAdminReadSLZ(after_query, many=True).data)

            add_admin_audit_record(
                user=self.request.user.pk,
                operation=OperationEnum.DELETE,
                target=OperationTarget.PLAT_USER,
                data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
                data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
            )

            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserProfile.DoesNotExist:
            return Response({"detail": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)


class AccountFeatureFlagManageViewSet(viewsets.GenericViewSet):
    """用户特性管理 API"""

    schema = None
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request):
        """获取用户特性列表"""
        feature_flags = AccountFeatureFlag.objects.all()
        slz = AccountFeatureFlagReadSLZ(feature_flags, many=True)
        return Response(slz.data)

    @atomic
    def update_or_create(self, request):
        """更新或创建用户特性"""
        slz = AccountFeatureFlagWriteSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        userid = data.get("userid")
        feature = data.get("feature")
        is_effect = data.get("isEffect", False)

        # 获取更新或创建前的用户特性
        before_query = AccountFeatureFlag.objects.filter(user=userid, name=feature)
        before_data = list(AccountFeatureFlagReadSLZ(before_query, many=True).data)

        AccountFeatureFlag.objects.update_or_create(user=userid, name=feature, defaults={"effect": is_effect})

        # 获取更新或创建后的用户特性
        after_query = AccountFeatureFlag.objects.filter(user=userid, name=feature)
        after_data = list(AccountFeatureFlagReadSLZ(after_query, many=True).data)

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.MODIFY_USER_FEATURE_FLAG,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, userid=None, feature=None, *args, **kwargs):
        """删除用户特性"""
        if not userid or not feature:
            return Response({"detail": "userid and feature are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 获取删除前的用户特性
            before_query = AccountFeatureFlag.objects.filter(user=userid, name=feature)
            before_data = list(AccountFeatureFlagReadSLZ(before_query, many=True).data)

            # 删除用户特性
            AccountFeatureFlag.objects.filter(user=userid, name=feature).delete()

            # 尝试获取删除后的用户特性
            after_query = AccountFeatureFlag.objects.filter(user=userid, name=feature)
            after_data = list(AccountFeatureFlagReadSLZ(after_query, many=True).data)

            add_admin_audit_record(
                user=self.request.user.pk,
                operation=OperationEnum.DELETE,
                target=OperationTarget.PLAT_USER,
                data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
                data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
            )

            return Response(status=status.HTTP_204_NO_CONTENT)
        except AccountFeatureFlag.DoesNotExist:
            return Response({"detail": "User feature flag not found"}, status=status.HTTP_404_NOT_FOUND)


class SystemAPIUserViewSet(viewsets.GenericViewSet):
    """系统 API 用户相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request, *args, **kwargs):
        """获取系统 API 用户列表"""
        sys_api_users = SysAPIClient.objects.annotate(
            bk_app_code=Coalesce(F("authenticatedappasclient__bk_app_code"), Value(""))
        ).values("name", "bk_app_code", "role", "updated")
        slz = SystemAPIUserReadSLZ(sys_api_users, many=True)
        return Response(slz.data)

    def update_or_create(self, request, *args, **kwargs):
        """创建系统 API 用户"""
        slz = SystemAPIUserWriteSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        username, bk_app_code, role = data["username"], data["bk_app_code"], data["role"]

        # 获取创建或更新前的系统 API 用户
        before_query = SysAPIClient.objects.filter(name=username, role=role).annotate(
            bk_app_code=Coalesce(F("authenticatedappasclient__bk_app_code"), Value(""))
        )
        before_data = list(SystemAPIUserReadSLZ(before_query, many=True).data)

        # 创建客户端
        client, _ = SysAPIClient.objects.get_or_create(name=username, defaults={"role": role})

        # 创建关系
        if bk_app_code:
            AuthenticatedAppAsClient.objects.update_or_create(
                client=client, bk_app_code=bk_app_code, defaults={"client": client}
            )

        # 获取创建或更新后的系统 API 用户
        after_query = SysAPIClient.objects.filter(name=username, role=role).annotate(
            bk_app_code=Coalesce(F("authenticatedappasclient__bk_app_code"), Value(""))
        )
        after_data = list(SystemAPIUserReadSLZ(after_query, many=True).data)

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, username=None, role=None, *args, **kwargs):
        """删除系统 API 用户"""
        if not username or not role:
            return Response({"detail": "Username and role are required"}, status=status.HTTP_400_BAD_REQUEST)

        # 查找对应的 SysAPIClient
        client_qs = SysAPIClient.objects.filter(name=username, role=role)
        if not client_qs.exists():
            return Response({"detail": "System API user not found"}, status=status.HTTP_404_NOT_FOUND)

        # 尝试获取删除前的系统 API 用户
        before_query = SysAPIClient.objects.filter(name=username, role=role).annotate(
            bk_app_code=Coalesce(F("authenticatedappasclient__bk_app_code"), Value(""))
        )
        before_data = list(SystemAPIUserReadSLZ(before_query, many=True).data)

        client_ids = list(client_qs.values_list("id", flat=True))

        # 删除关系
        AuthenticatedAppAsClient.objects.filter(client_id__in=client_ids).delete()
        # 删除系统 API 用户
        SysAPIClient.objects.filter(name=username, role=role).delete()

        # 尝试获取删除后的系统 API 用户
        after_query = SysAPIClient.objects.filter(name=username, role=role).annotate(
            bk_app_code=Coalesce(F("authenticatedappasclient__bk_app_code"), Value(""))
        )
        after_data = list(SystemAPIUserReadSLZ(after_query, many=True).data)

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
