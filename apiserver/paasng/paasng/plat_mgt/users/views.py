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

from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.db.transaction import atomic
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import AccountFeatureFlag, UserProfile
from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.infras.sysapi_client.constants import ClientRole
from paasng.infras.sysapi_client.models import AuthenticatedAppAsClient, ClientPrivateToken, SysAPIClient
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_mgt.users.serializers import (
    BulkCreatePlatformManagerSLZ,
    CreateSystemAPIUserSLZ,
    PlatformManagerSLZ,
    SystemAPIUserSLZ,
    UpdateUserFeatureFlagSLZ,
    UserFeatureFlagSLZ,
)

logger = logging.getLogger(__name__)


class PlatformManagerViewSet(viewsets.GenericViewSet):
    """平台管理员相关 API"""

    # 需要平台管理权限才能访问
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="获取平台管理员列表",
        responses={status.HTTP_200_OK: PlatformManagerSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取平台管理员列表"""
        admin_profiles = (
            UserProfile.objects.filter(
                role__in=[SiteRole.ADMIN.value, SiteRole.SUPER_USER.value],
            )
            .order_by("-created")
            .values()
        )
        slz = PlatformManagerSLZ(admin_profiles, many=True)
        return Response(slz.data)

    @atomic
    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="批量创建平台管理员",
        request_body=BulkCreatePlatformManagerSLZ,
        responses={status.HTTP_201_CREATED: None},
    )
    def bulk_create(self, request, *args, **kwargs):
        """批量创建平台管理员"""
        slz = BulkCreatePlatformManagerSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        users = slz.validated_data["users"]

        # 创建用户名到用户ID的映射
        user_to_id = {user: user_id_encoder.encode(settings.USER_TYPE, user) for user in users}
        user_ids = list(user_to_id.values())

        # 获取创建前的数据 - 查询数据库中已存在的用户
        existing_profiles = UserProfile.objects.filter(user__in=user_ids)
        existing_user_ids = set(existing_profiles.values_list("user", flat=True))

        # 检查是否存在未登录过平台的用户, 如果存在则返回错误
        non_existing_users = [user for user, user_id in user_to_id.items() if user_id not in existing_user_ids]
        if non_existing_users:
            return Response(
                {"detail": f"user {', '.join(non_existing_users)} has not logged in to the platform yet"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 准备审计数据并更新用户角色
        role = SiteRole.ADMIN.value
        before_data = []
        profiles_to_update = []

        id_to_name = {user_id: user for user, user_id in user_to_id.items()}

        for profile in existing_profiles:
            user = id_to_name.get(profile.user)
            before_data.append({"user": user, "role": profile.role})
            profile.role = role
            profiles_to_update.append(profile)

        # 批量更新用户角色
        UserProfile.objects.bulk_update(profiles_to_update, ["role"])

        # 构建更新后的审计数据
        after_data = [{"user": user, "role": role} for user in users]

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="删除平台管理员",
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def destroy(self, request, user, *args, **kwargs):
        """删除平台管理员"""
        # 将用户名编码为userid
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)

        # 获取删除前的用户信息
        userprofile = UserProfile.objects.filter(user=user_id).first()
        if not userprofile:
            return Response({"detail": f"User {user} not found"}, status=status.HTTP_404_NOT_FOUND)

        # 如果用户的权限已经不是管理员权限，直接返回 204
        if userprofile.role not in [SiteRole.ADMIN.value, SiteRole.SUPER_USER.value]:
            return Response(status=status.HTTP_204_NO_CONTENT)

        # 构建审计数据
        before_data = {"user": user, "role": userprofile.role}
        after_data = {"user": user, "role": SiteRole.USER.value}

        # 删除用户, 将权限更改为普通用户
        userprofile.role = SiteRole.USER.value
        userprofile.save(update_fields=["role"])

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountFeatureFlagManageViewSet(viewsets.GenericViewSet):
    """用户特性管理 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="获取用户特性列表",
        responses={status.HTTP_200_OK: UserFeatureFlagSLZ(many=True)},
    )
    def list(self, request):
        """获取用户特性列表"""
        feature_flags = AccountFeatureFlag.objects.all()
        slz = UserFeatureFlagSLZ(feature_flags, many=True)
        return Response(slz.data)

    @atomic
    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="更新或创建用户特性",
        request_body=UpdateUserFeatureFlagSLZ,
        responses={status.HTTP_201_CREATED: None},
    )
    def upsert(self, request):
        """更新或创建用户特性"""
        slz = UpdateUserFeatureFlagSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        user, feature, is_effect = data["user"], data["feature"], data["is_effect"]
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)

        # 获取更新或创建前的用户特性
        feature_flag = AccountFeatureFlag.objects.filter(user=user_id, name=feature).first()

        # 构建审计数据
        before_data = []
        if feature_flag:
            before_data = [{"user": user, "feature": feature, "is_effect": feature_flag.effect}]

        # 更新或创建用户特性
        if feature_flag:
            # 更新特性
            feature_flag.effect = is_effect
            feature_flag.save(update_fields=["effect"])
        else:
            # 创建特性
            feature_flag = AccountFeatureFlag(user=user_id, name=feature, effect=is_effect)
            feature_flag.save()

        # 构建更新后的审计数据
        after_data = [{"user": user, "feature": feature, "is_effect": is_effect}]

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.MODIFY_USER_FEATURE_FLAG,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )

        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="删除用户特性",
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def destroy(self, request, user=None, feature=None, *args, **kwargs):
        """删除用户特性"""

        # 将用户名编码为 userid
        user_id = user_id_encoder.encode(settings.USER_TYPE, user)
        # 查询db中是否存有该用户特性
        feature_flag = AccountFeatureFlag.objects.filter(user=user_id, name=feature).first()
        if not feature_flag:
            return Response({"detail": "Feature flag not found"}, status=status.HTTP_404_NOT_FOUND)

        # 构建审计数据
        before_data = [{"user": user, "feature": feature, "is_effect": feature_flag.effect}]

        try:
            # 删除用户特性
            feature_flag.delete()
        except Exception:
            logger.exception("Failed to delete user feature flag")
            return Response(
                {"detail": "Failed to delete user feature flag"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class SystemAPIUserViewSet(viewsets.GenericViewSet):
    """系统 API 用户相关 API"""

    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="获取系统 API 用户列表",
        responses={status.HTTP_200_OK: SystemAPIUserSLZ(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """获取系统 API 用户列表"""
        # 查询所有系统 API 客户端
        sys_api_clients = SysAPIClient.objects.all()
        # 获取客户端ID列表
        client_ids = [client.id for client in sys_api_clients]
        # 查询应用认证关系
        app_clients = AuthenticatedAppAsClient.objects.filter(client_id__in=client_ids)
        app_code_map = {client.client: client.bk_app_code for client in app_clients}
        # 查询私有令牌
        private_tokens = ClientPrivateToken.objects.filter(client_id__in=client_ids)
        token_map = {client.client: client.token for client in private_tokens}

        # 组装数据
        result = []
        for client in sys_api_clients:
            client_data = {
                "name": client.name,
                "bk_app_code": app_code_map.get(client.id, ""),
                "private_token": token_map.get(client.id, ""),
                "role": client.role,
                "updated": client.updated,
            }
            result.append(client_data)

        slz = SystemAPIUserSLZ(result, many=True)
        return Response(slz.data)

    @atomic
    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="创建系统 API 用户",
        request_body=CreateSystemAPIUserSLZ,
        responses={status.HTTP_201_CREATED: None},
    )
    def create(self, request, *args, **kwargs):
        """创建系统 API 用户"""
        slz = CreateSystemAPIUserSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        user, bk_app_code, role = data["user"], data["bk_app_code"], data["role"]

        # 验证role是否为ClientRole中的有效值
        try:
            role_int = int(role)
            if role_int not in ClientRole.get_values():
                return Response(
                    {"detail": f"Invalid role: {role}. Must be one of {ClientRole.get_values()}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {"detail": f"Invalid role format: {role}. Must be an integer."}, status=status.HTTP_400_BAD_REQUEST
            )

        # 获取创建前的系统 API 用户数据
        existing_client = SysAPIClient.objects.filter(name=user).first()
        before_data = []

        if existing_client:
            # 单独查询关联的应用
            existing_app_client = AuthenticatedAppAsClient.objects.filter(client=existing_client).first()
            existing_bk_app_code = existing_app_client.bk_app_code if existing_app_client else ""

            before_data = [
                {"user": existing_client.name, "bk_app_code": existing_bk_app_code, "role": existing_client.role}
            ]

        # 创建或更新客户端
        client, created = SysAPIClient.objects.get_or_create(name=user, defaults={"role": role})
        # 如果不是新创建的客户端，则更新角色
        if not created and client.role != role:
            client.role = role
            client.save(update_fields=["role"])

        # 创建或更新应用关系
        if bk_app_code:
            AuthenticatedAppAsClient.objects.update_or_create(client=client, defaults={"bk_app_code": bk_app_code})

        # 构建审计数据
        after_data = [{"user": user, "bk_app_code": bk_app_code, "role": role}]

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )

        return Response(status=status.HTTP_201_CREATED)

    @atomic
    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="更新系统 API 用户的权限",
        request_body=CreateSystemAPIUserSLZ,
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def update(self, request, *args, **kwargs):
        # 验证请求数据
        slz = CreateSystemAPIUserSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        # 获取请求参数
        user, role = data["user"], data["role"]

        # 验证role是否为ClientRole中的有效值
        try:
            role_int = int(role)
            if role_int not in ClientRole.get_values():
                return Response(
                    {"detail": f"Invalid role: {role}. Must be one of {ClientRole.get_values()}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {"detail": f"Invalid role format: {role}. Must be an integer."}, status=status.HTTP_400_BAD_REQUEST
            )

        # 检查要更新的用户是否存在
        client = SysAPIClient.objects.filter(name=user).first()
        if not client:
            return Response({"detail": f"System API user '{user}' not found"}, status=status.HTTP_404_NOT_FOUND)

        # 构建审计数据
        existing_app_client = AuthenticatedAppAsClient.objects.filter(client=client).first()
        existing_bk_app_code = existing_app_client.bk_app_code if existing_app_client else ""
        before_data = [{"user": client.name, "bk_app_code": existing_bk_app_code, "role": client.role}]

        # 更新角色
        if client.role != role:
            client.role = role
            client.save(update_fields=["role"])

        # 构建审计数据
        after_data = [{"user": user, "bk_app_code": existing_bk_app_code, "role": role}]

        # 记录审计日志
        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
            data_after=DataDetail(type=DataType.RAW_DATA, data=after_data),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        tags=["plat_mgt.users"],
        operation_description="删除系统 API 用户",
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    @atomic
    def destroy(self, request, user=None, *args, **kwargs):
        """删除系统 API 用户"""
        client = SysAPIClient.objects.filter(name=user).first()
        if not client:
            return Response({"detail": "System API user not found"}, status=status.HTTP_404_NOT_FOUND)

        # 构建审计数据
        app_client = AuthenticatedAppAsClient.objects.filter(client=client).first()
        bk_app_code = app_client.bk_app_code if app_client else ""
        before_data = [{"user": client.name, "bk_app_code": bk_app_code, "role": client.role}]

        # 删除关系
        AuthenticatedAppAsClient.objects.filter(client=client).delete()
        # 删除系统 API 用户
        client.delete()

        add_admin_audit_record(
            user=self.request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.PLAT_USER,
            data_before=DataDetail(type=DataType.RAW_DATA, data=before_data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
