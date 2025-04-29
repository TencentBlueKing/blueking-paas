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


from typing import Any, Dict

from django.conf import settings
from rest_framework import serializers

from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag, UserProfile
from paasng.infras.sysapi_client.constants import ClientRole

# --------- 平台管理员相关序列化器 ---------


class PlatformManagerSLZ(serializers.Serializer):
    """列出平台管理员序列化器"""

    user = serializers.CharField(source="user.username", help_text="用户 ID")
    created = serializers.DateTimeField(help_text="添加时间")
    tenant_id = serializers.CharField(help_text="租户 ID")


class CreatePlatformManagerSLZ(serializers.Serializer):
    """创建平台管理员序列化器"""

    user = serializers.CharField(help_text="用户 ID")
    tenant_id = serializers.CharField(help_text="租户 ID", required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """根据多租户模式验证和填充租户ID"""
        if not settings.ENABLE_MULTI_TENANT_MODE:
            # 如果多租户模式未启用，则将租户 ID 设置为默认值
            attrs["tenant_id"] = DEFAULT_TENANT_ID
        # 开启多租户, tenant_id 为必填项
        elif not attrs.get("tenant_id"):
            raise serializers.ValidationError({"tenant_id": "Tenant ID is required when multi-tenant mode is enabled"})
        return attrs


# --------- 用户特性相关序列化器 ---------


class AccountFeatureFlagSLZ(serializers.Serializer):
    """用户特性序列化器"""

    id = serializers.IntegerField(read_only=True)
    user = serializers.CharField(source="user.username", read_only=True)
    tenant_id = serializers.SerializerMethodField(help_text="租户 ID")
    feature = serializers.CharField(source="name")
    is_effect = serializers.BooleanField(source="effect")
    created = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S")
    default_feature_flag = serializers.SerializerMethodField()

    def get_tenant_id(self, obj: AccountFeatureFlag) -> str:
        """获取租户 ID"""
        profile = UserProfile.objects.filter(user=obj.user).first()
        return profile.tenant_id if profile else ""

    def get_default_feature_flag(self, obj: AFF) -> bool:
        """根据特性名称获取其默认配置值"""
        # 从 AccountFeatureFlag 获取所有特性的默认值
        account_feature_default_flags = AFF.get_default_flags()
        # 使用特性名称(obj.name)从默认值中获取对应的配置
        return account_feature_default_flags.get(obj.name, False)


class UpsertAccountFeatureFlagSLZ(serializers.Serializer):
    """更新用户特性序列化器"""

    user = serializers.CharField(help_text="用户名称")
    feature = serializers.CharField(help_text="特性名称")
    is_effect = serializers.BooleanField(default=False, help_text="是否生效")

    def validate_feature(self, value):
        """检查特性名称是否在 AccountFeatureFlag 中定义"""
        choices = AFF.get_choices()
        valid_features = [choice[0] for choice in choices]
        if value not in valid_features:
            raise serializers.ValidationError(
                f"Invalid feature '{value}'. Must be one of: {', '.join(valid_features)}"
            )
        return value


class AccountFeatureFlagKindSLZ(serializers.Serializer):
    """返回所有用户特性种类序列化器"""

    value = serializers.CharField(help_text="特性名称")
    label = serializers.CharField(help_text="特性描述")
    default_flag = serializers.BooleanField(help_text="默认值")


# --------- 已授权应用相关序列化器 ---------


class SystemAPIClientSLZ(serializers.Serializer):
    """已授权应用序列化器"""

    bk_app_code = serializers.CharField(help_text="应用 ID", required=False)
    role = serializers.CharField(help_text="权限")
    updated = serializers.DateTimeField(help_text="添加时间")


class UpsertSystemAPIClientSLZ(serializers.Serializer):
    """创建或更新已授权应用序列化器"""

    bk_app_code = serializers.CharField(help_text="应用 ID", required=True)
    role = serializers.IntegerField(help_text="权限")

    def validate_role(self, value):
        """检查角色是否在 ClientRole 中定义"""
        valid_roles = ClientRole.get_values()
        if value not in valid_roles:
            raise serializers.ValidationError(
                f"Invalid role '{value}'. Must be one of: {', '.join(str(r) for r in valid_roles)}"
            )
        return value


# --------- 系统 API 权限相关序列化器 ---------
class SystemAPIClientRoleSLZ(serializers.Serializer):
    """已授权应用权限序列化器"""

    value = serializers.IntegerField(help_text="角色 ID")
    label = serializers.CharField(help_text="角色描述")
