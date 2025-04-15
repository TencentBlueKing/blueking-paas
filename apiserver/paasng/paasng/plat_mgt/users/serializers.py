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


from rest_framework import serializers

from paasng.infras.accounts.constants import AccountFeatureFlag
from paasng.infras.sysapi_client.constants import ClientRole

# --------- 平台管理员相关序列化器 ---------


class PlatformManagerSLZ(serializers.Serializer):
    """列出平台管理员序列化器"""

    user = serializers.CharField(source="user.username", help_text="用户 ID")
    created = serializers.DateTimeField(help_text="添加时间")
    tenant_id = serializers.CharField(help_text="租户 ID")


class BulkCreatePlatformManagerSLZ(serializers.Serializer):
    """批量创建平台管理员序列化器"""

    users = serializers.ListField(child=serializers.CharField(), min_length=1, help_text="管理员用户名列表")


# --------- 用户特性相关序列化器 ---------


class UserFeatureFlagSLZ(serializers.Serializer):
    """用户特性序列化器"""

    id = serializers.IntegerField(read_only=True)
    user = serializers.CharField(source="user.username", read_only=True)
    feature = serializers.CharField(source="name")
    is_effect = serializers.BooleanField(source="effect")
    created = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S")
    default_feature_flag = serializers.SerializerMethodField()

    def get_default_feature_flag(self, obj: AccountFeatureFlag) -> bool:
        """根据特性名称获取其默认配置值"""
        # 从 AccountFeatureFlag 获取所有特性的默认值
        account_feature_default_flags = AccountFeatureFlag.get_default_flags()
        # 使用特性名称(obj.name)从默认值中获取对应的配置
        return account_feature_default_flags.get(obj.name, False)


class UpsertUserFeatureFlagSLZ(serializers.Serializer):
    """更新用户特性序列化器"""

    user = serializers.CharField(help_text="用户名称")
    feature = serializers.CharField(help_text="特性名称")
    is_effect = serializers.BooleanField(default=False, help_text="是否生效")

    def validate_feature(self, value):
        """检查特性名称是否在 AccountFeatureFlag 中定义"""
        choices = AccountFeatureFlag.get_choices()
        valid_features = [choice[0] for choice in choices]
        if value not in valid_features:
            raise serializers.ValidationError(
                f"Invalid feature '{value}'. Must be one of: {', '.join(valid_features)}"
            )
        return value


# --------- 系统 API 用户相关序列化器 ---------


class SystemAPIUserSLZ(serializers.Serializer):
    """系统 API 用户序列化器"""

    user = serializers.CharField(source="name", help_text="用户 ID")
    bk_app_code = serializers.CharField(help_text="应用 ID", required=False)
    private_token = serializers.CharField(help_text="私钥", required=False)
    role = serializers.CharField(help_text="权限")
    updated = serializers.DateTimeField(help_text="添加时间")


class UpsertSystemAPIUserSLZ(serializers.Serializer):
    """创建或更新系统 API 用户序列化器"""

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
