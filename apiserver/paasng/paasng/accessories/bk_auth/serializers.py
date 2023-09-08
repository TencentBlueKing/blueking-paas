# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from datetime import datetime

from rest_framework import serializers


def desensitize_secret(secret: str) -> str:
    """密钥脱敏展示"""
    # 应用密钥，仅展示前4、后4位，中间用12个 * 代替
    return secret[:4] + "************" + secret[-4:]


class AppSecretSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    bk_app_code = serializers.CharField(help_text="应用 ID")
    bk_app_secret = serializers.CharField(help_text="应用密钥，仅展示前4、后4位，中间用12个 * 代替")
    enabled = serializers.BooleanField(help_text="是否启用")
    created_at = serializers.DateTimeField(help_text="创建时间")

    def to_representation(self, obj):
        if isinstance(obj.created_at, str):
            # bkAuth API 返回的时间格式需要格式化
            obj.created_at = datetime.strptime(obj.created_at, "%Y-%m-%dT%H:%M:%SZ")
        result = super().to_representation(obj)

        # 应用密钥脱敏展示
        result["bk_app_secret"] = desensitize_secret(obj.bk_app_secret)
        return result


class AppSecretStatusSLZ(serializers.Serializer):
    enabled = serializers.BooleanField()


class AppSecretIdSLZ(serializers.Serializer):
    id = serializers.IntegerField()


class AppSecretInEnvSLZ(serializers.Serializer):
    module = serializers.CharField(help_text="模块")
    environment = serializers.CharField(help_text="环境")
    bk_app_secret = serializers.CharField(help_text="密钥")
    latest_deployed_at = serializers.DateTimeField(help_text="最近部署时间")

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["bk_app_secret"] = desensitize_secret(obj['bk_app_secret'])
        return result


class BulitinAppSecretSLZ(serializers.Serializer):
    bulitin_app_secret = serializers.CharField(help_text="内置密钥")
    deployed_secret_list = serializers.ListField(child=AppSecretInEnvSLZ())

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["bulitin_app_secret"] = desensitize_secret(obj['bulitin_app_secret'])
        return result
