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

from bkpaas_auth.core.encoder import user_id_encoder
from rest_framework import serializers


class PlatMgtAdminReadSLZ(serializers.Serializer):
    """平台管理员序列化器"""

    userId = serializers.CharField(help_text="用户 ID")
    username = serializers.CharField(help_text="用户名")
    tenants = serializers.CharField(help_text="所属租户")
    addTime = serializers.DateTimeField(help_text="添加时间")

    @staticmethod
    def get_user_tenant(user_id: str) -> str:
        """获取用户所属的租户"""
        # 先直接返回system, 查询租户信息
        return "system"

    @staticmethod
    def extract_user_data(profile) -> Dict[str, Any]:
        """从用户配置文件提取标准数据字段"""

        user_id = profile.user
        try:
            _, username = user_id_encoder.decode(profile.user)
        except Exception:
            username = "Unknown User"

        # 获取用户所属租户
        tenants = PlatMgtAdminReadSLZ.get_user_tenant(user_id)
        created_time = getattr(profile, "created", None)

        return {
            "userId": user_id,
            "username": username,
            "tenants": tenants,
            "addTime": created_time,
        }

    @classmethod
    def from_profile(cls, profile):
        """从单个用户配置文件创建序列化器实例"""
        data = cls.extract_user_data(profile)
        return cls(instance=data)

    @classmethod
    def from_profiles(cls, profiles):
        """批量从用户配置文件列表创建序列化器实例"""
        extracted_data = [cls.extract_user_data(profile) for profile in profiles]
        return cls(instance=extracted_data, many=True)


class PlatMgtAdminWriteSLZ(serializers.Serializer):
    """专用于批量创建平台管理员的序列化器"""

    username_list = serializers.ListField(child=serializers.CharField(), help_text="管理员用户名列表")

    @classmethod
    def for_bulk_create(cls, data):
        """创建用于批量创建的序列化器实例"""
        return cls(data={"username_list": data.get("username_list", [])})

    def validate(self, attrs):
        # 如果是批量创建上下文，只验证 username_list
        if self.context.get("for_bulk_create") and not attrs.get("username_list"):
            raise serializers.ValidationError({"username_list": "This field is required"})
        return attrs


class AccountFeatureFlagReadSLZ(serializers.Serializer):
    """用户特性序列化器"""

    userId = serializers.CharField(source="user", read_only=True)
    username = serializers.CharField(write_only=True)
    feature = serializers.CharField(source="name")
    isEffect = serializers.BooleanField(source="effect")
    tenants = serializers.CharField(default="system", read_only=True)
    addTime = serializers.DateTimeField(source="created", read_only=True, format="%Y-%m-%d %H:%M:%S")
    # 获取用户特性的默认值
    default_feature = serializers.BooleanField(default=False, read_only=True)

    def to_representation(self, instance):
        """处理响应数据"""
        data = super().to_representation(instance)
        # 将用户ID解码为用户名
        if hasattr(instance, "user"):
            try:
                _, username = user_id_encoder.decode(instance.user)
                data["username"] = username
            except Exception:
                data["username"] = "未知用户"
        return data


class AccountFeatureFlagWriteSLZ(serializers.Serializer):
    """用户特性创建序列化器，专门用于处理创建和删除请求"""

    username = serializers.CharField(help_text="用户名")
    feature = serializers.CharField(help_text="特性名称")
    isEffect = serializers.BooleanField(default=False, help_text="是否生效")

    def validate(self, attrs):
        """验证数据"""
        if not attrs.get("username"):
            raise serializers.ValidationError({"username": "Username is required"})
        if not attrs.get("feature"):
            raise serializers.ValidationError({"feature": "Feature name is required"})
        return attrs


class SystemAPIUserReadSLZ(serializers.Serializer):
    """系统 API 用户序列化器"""


class SystemAPIUserWriteSLZ(serializers.Serializer):
    """系统 API 用户创建序列化器"""

    bk_app_code = serializers.CharField(help_text="应用 ID", required=False)
    username = serializers.CharField(help_text="用户名")
    permission = serializers.CharField(help_text="权限")
