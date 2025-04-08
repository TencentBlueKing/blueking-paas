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


from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from rest_framework import serializers

from paasng.infras.accounts.constants import AccountFeatureFlag


class PlatMgtAdminReadSLZ(serializers.Serializer):
    """平台管理员序列化器"""

    userid = serializers.CharField(source="user", help_text="用户 ID")
    created = serializers.DateTimeField(help_text="添加时间")


class PlatMgtAdminWriteSLZ(serializers.Serializer):
    """专用于批量创建平台管理员的序列化器"""

    username_list = serializers.ListField(child=serializers.CharField(), help_text="管理员用户名列表")

    def validate_username_list(self, username_list):
        """验证用户名列表中的用户名的用户类型是否正确"""
        invalid_usernames = []

        for userid in username_list:
            try:
                user_type, _ = user_id_encoder.decode(userid)
            except Exception:
                invalid_usernames.append(userid)
                continue

            if user_type != settings.USER_TYPE:
                invalid_usernames.append(userid)

        if invalid_usernames:
            raise serializers.ValidationError(f"Invalid usernames: {', '.join(invalid_usernames)}")
        return username_list


class AccountFeatureFlagReadSLZ(serializers.Serializer):
    """用户特性序列化器"""

    userid = serializers.CharField(source="user", read_only=True)
    feature = serializers.CharField(source="name")
    isEffect = serializers.BooleanField(source="effect")
    created = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S")
    default_feature = serializers.SerializerMethodField()

    def get_default_feature(self, obj):
        """根据特性名称获取其默认配置值"""
        # 从 AccountFeatureFlag 获取所有特性的默认值
        default_flags = AccountFeatureFlag.get_default_flags()
        # 使用特性名称(obj.name)从默认值中获取对应的配置
        return default_flags.get(obj.name, False)


class AccountFeatureFlagWriteSLZ(serializers.Serializer):
    """用户特性创建序列化器，专门用于处理创建和删除请求"""

    userid = serializers.CharField(help_text="用户id")
    feature = serializers.CharField(help_text="特性名称")
    isEffect = serializers.BooleanField(default=False, help_text="是否生效")

    def validate_userid(self, userid):
        try:
            _, _ = user_id_encoder.decode(userid)
        except Exception:
            raise serializers.ValidationError("Invalid user ID")
        return userid


class SystemAPIUserReadSLZ(serializers.Serializer):
    """系统 API 用户序列化器"""

    username = serializers.CharField(source="name", help_text="用户 ID")
    bk_app_code = serializers.CharField(help_text="应用 ID", required=False)
    private_token = serializers.CharField(help_text="私钥", required=False)
    role = serializers.CharField(help_text="权限")
    updated = serializers.DateTimeField(help_text="添加时间")


class SystemAPIUserWriteSLZ(serializers.Serializer):
    """系统 API 用户创建序列化器"""

    bk_app_code = serializers.CharField(help_text="应用 ID", required=False, allow_blank=True)
    username = serializers.CharField(help_text="用户名")
    role = serializers.CharField(help_text="权限")
