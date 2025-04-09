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

# --------- 平台管理员相关序列化器 ---------


class PlatformAdminField(serializers.Serializer):
    user = serializers.CharField(source="user.username", help_text="用户 ID")
    created = serializers.DateTimeField(help_text="添加时间")


class ListPlatformAdminOutputSLZ(PlatformAdminField):
    """列出平台管理员序列化器"""


class BulkCreatePlatformAdminInputSLZ(serializers.Serializer):
    user_list = serializers.ListField(child=serializers.CharField(), help_text="管理员用户名列表")


class BulkCreatePlatformAdminOutputSLZ(PlatformAdminField):
    """列出平台管理员序列化器"""


class DestroyPlatformAdminOutputSLZ(PlatformAdminField):
    """列出平台管理员序列化器"""


# --------- 用户特性相关序列化器 ---------


class UserFeatureFlagField(serializers.Serializer):
    user = serializers.CharField(source="user.username", read_only=True)
    feature = serializers.CharField(source="name")
    isEffect = serializers.BooleanField(source="effect")
    created = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S")
    default_feature_flags = serializers.SerializerMethodField()

    def get_default_feature_flags(self, obj):
        """根据特性名称获取其默认配置值"""
        # 从 AccountFeatureFlag 获取所有特性的默认值
        default_flags = AccountFeatureFlag.get_default_flags()
        # 使用特性名称(obj.name)从默认值中获取对应的配置
        return default_flags.get(obj.name, False)


class ListUserFeatureFlagOutputSLZ(UserFeatureFlagField):
    """列出用户特性序列化器"""


class UpdateUserFeatureFlagOutputSLZ(UserFeatureFlagField):
    """列出用户特性序列化器"""


class UpdateUserFeatureFlagInputSLZ(serializers.Serializer):
    user = serializers.CharField(help_text="用户名称")
    feature = serializers.CharField(help_text="特性名称")
    isEffect = serializers.BooleanField(default=False, help_text="是否生效")


class DestroyUserFeatureFlagOutputSLZ(UserFeatureFlagField):
    """列出用户特性序列化器"""


# --------- 系统 API 用户相关序列化器 ---------


class SystemAPIUserField(serializers.Serializer):
    user = serializers.CharField(source="name", help_text="用户 ID")
    bk_app_code = serializers.CharField(help_text="应用 ID", required=False)
    private_token = serializers.CharField(help_text="私钥", required=False)
    role = serializers.CharField(help_text="权限")
    updated = serializers.DateTimeField(help_text="添加时间")


class ListSystemAPIUserOutputSLZ(SystemAPIUserField):
    """列出系统 API 用户序列化器"""


class CreateSystemAPIUserOutputSLZ(SystemAPIUserField):
    """列出系统 API 用户序列化器"""


class CreateSystemAPIUserInputSLZ(serializers.Serializer):
    bk_app_code = serializers.CharField(help_text="应用 ID", required=False, allow_blank=True)
    user = serializers.CharField(help_text="用户名")
    role = serializers.CharField(help_text="权限")


class DestroySystemAPIUserOutputSLZ(SystemAPIUserField):
    """列出系统 API 用户序列化器"""
