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

from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings as django_settings
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
)

logger = logging.getLogger(__name__)
USER_TYPE = getattr(django_settings, "USER_TYPE", "default")


class PlatMgtAdminViewSet(viewsets.GenericViewSet):
    """平台管理员相关 API"""

    # 需要平台管理权限才能访问
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request, *args, **kwargs):
        """获取平台管理员列表"""
        admin_profiles = UserProfile.objects.filter(
            role__in=[SiteRole.ADMIN.value, SiteRole.SUPER_USER.value],
        ).order_by("-created")
        slz = PlatMgtAdminReadSLZ.from_profiles(admin_profiles)
        return Response(slz.data)

    @atomic
    def bulk_create(self, request, *args, **kwargs):
        """批量创建平台管理员"""
        slz = PlatMgtAdminWriteSLZ(data=request.data, context={"for_bulk_create": True})
        slz.is_valid(raise_exception=True)
        provider_type = USER_TYPE
        role = SiteRole.ADMIN.value

        created_profiles = []
        for username in slz.data["username_list"]:
            user_id = user_id_encoder.encode(provider_type, username)
            obj, _ = UserProfile.objects.update_or_create(user=user_id, defaults={"role": role})
            obj.refresh_from_db()
            created_profiles.append(obj)

        results_serializer = PlatMgtAdminReadSLZ.from_profiles(created_profiles)

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.PLAT_USER,
            data_after=DataDetail(type=DataType.RAW_DATA, data=list(results_serializer.data)),
        )
        return Response(results_serializer.data)

    def destroy(self, request, username, *args, **kwargs):
        """删除平台管理员"""
        if not username:
            return Response({"detail": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = user_id_encoder.encode(USER_TYPE, username)

        data_before = PlatMgtAdminReadSLZ.from_profile(UserProfile.objects.get(user=user_id)).data

        # 删除用户
        UserProfile.objects.filter(user=user_id).delete()

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=data_before),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountFeatureFlagManageViewSet(viewsets.GenericViewSet):
    """用户特性管理 API"""

    schema = None
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request):
        """获取用户特性列表"""
        feature_flags = AccountFeatureFlag.objects.all()
        return Response(AccountFeatureFlagReadSLZ(feature_flags, many=True, context={"request": request}).data)

    def update_or_create(self, request):
        """更新或创建用户特性"""
        slz = AccountFeatureFlagWriteSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        username = data.get("username")
        feature = data.get("feature")
        is_effect = data.get("isEffect", False)

        user_id = user_id_encoder.encode(USER_TYPE, username)

        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data=AccountFeatureFlagReadSLZ(AccountFeatureFlag.objects.filter(user=user_id)).data,
        )

        AccountFeatureFlag.objects.update_or_create(user=user_id, name=feature, defaults={"effect": is_effect})

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.MODIFY_USER_FEATURE_FLAG,
            target=OperationTarget.PLAT_USER,
            attribute=username,
            data_before=data_before,
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data=AccountFeatureFlagReadSLZ(AccountFeatureFlag.objects.filter(user=user_id)).data,
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, username=None, feature=None, *args, **kwargs):
        """删除用户特性"""
        if not username or not feature:
            return Response({"detail": "Username and feature are required"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = user_id_encoder.encode(USER_TYPE, username)
        data_before = DataDetail(
            type=DataType.RAW_DATA,
            data=AccountFeatureFlagReadSLZ(AccountFeatureFlag.objects.filter(user=user_id)).data,
        )

        # 删除用户特性
        AccountFeatureFlag.objects.filter(user=user_id, name=feature).delete()

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.PLAT_USER,
            attribute=username,
            data_before=data_before,
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data=AccountFeatureFlagReadSLZ(AccountFeatureFlag.objects.filter(user=user_id)).data,
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class SystemAPIUserViewSet(viewsets.GenericViewSet):
    """系统 API 用户相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def list(self, request, *args, **kwargs):
        """获取系统 API 用户列表"""

    def update_or_create(self, request, *args, **kwargs):
        """创建系统 API 用户"""
        # data = request.data
        # bk_app_code = data.get("bk_app_code")
        # username = data.get("username") or self._get_default_username(bk_app_code)
        # role = data.get("role")

        # if not bk_app_code or not role:
        #     return Response({"detail": "bk_app_code and role are required"}, status=status.HTTP_400_BAD_REQUEST)

        # # 创建客户端
        # client, _ = SysAPIClient.objects.get_or_create(name=username, defaults={"role": role})
        # logger.info(f"user: {client.name} created.")

        # # 创建关系
        # AuthenticatedAppAsClient.objects.update_or_create(bk_app_code=bk_app_code, defaults={"client": client})
        # logger.info(f"app-user relation: {bk_app_code}-{client.name} created.")

        # return Response(status=status.HTTP_201_CREATED)

    def destroy(self, request, username=None, permission=None, *args, **kwargs):
        """删除系统 API 用户"""
        if not username or not permission:
            return Response({"detail": "Username and permission are required"}, status=status.HTTP_400_BAD_REQUEST)

        # 删除系统 API 用户
        SysAPIClient.objects.filter(name=username, role=permission).delete()

        # 删除关系
        AuthenticatedAppAsClient.objects.filter(client__name=username).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
