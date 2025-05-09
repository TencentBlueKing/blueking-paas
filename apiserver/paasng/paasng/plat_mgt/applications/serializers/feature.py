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

from paasng.platform.applications.constants import AppFeatureFlag


class ApplicationFeatureFlagSLZ(serializers.Serializer):
    """平台管理 - 应用特性序列化器"""

    name = serializers.CharField(help_text="特性名称")
    label = serializers.SerializerMethodField(help_text="特性标签")
    effect = serializers.BooleanField(help_text="特性的启用状态")
    default_feature_flag = serializers.SerializerMethodField(help_text="特性默认值")

    def get_label(self, obj) -> str:
        """获取特性标签"""
        return AppFeatureFlag.get_feature_label(obj["name"])

    def get_default_feature_flag(self, obj) -> bool:
        """获取特性默认值"""
        return AppFeatureFlag.get_default_flags().get(obj["name"], False)


class UpdateApplicationFeatureFlagSLZ(serializers.Serializer):
    """平台管理 - 更新应用特性序列化器"""

    name = serializers.CharField(help_text="特性名称")
    effect = serializers.BooleanField(help_text="特性的启用状态")

    def validate_name(self, value: str) -> str:
        """验证特性名称"""
        valid_names = AppFeatureFlag.get_default_flags().keys()
        if value not in valid_names:
            raise serializers.ValidationError(f"Invalid feature name: {value}")
        return value
