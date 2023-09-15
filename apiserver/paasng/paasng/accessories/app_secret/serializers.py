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
from rest_framework import serializers


class SecretField(serializers.ReadOnlyField):
    def to_representation(self, value):
        if len(value) < 8:
            return "*" * 12

        # 应用密钥，仅展示前4、后4位，中间用12个 * 代替
        return value[:4] + "*" * 12 + value[-4:]


class AppSecretSLZ(serializers.Serializer):
    id = serializers.IntegerField()
    bk_app_code = serializers.CharField(help_text="应用 ID")
    bk_app_secret = SecretField(help_text="应用密钥，仅展示前4、后4位，中间用12个 * 代替")
    enabled = serializers.BooleanField(help_text="是否启用")
    created_at = serializers.DateTimeField(help_text="创建时间")


class AppSecretStatusSLZ(serializers.Serializer):
    enabled = serializers.BooleanField()


class AppSecretIdSLZ(serializers.Serializer):
    id = serializers.IntegerField()


class DeployedSecretSLZ(serializers.Serializer):
    module = serializers.CharField(help_text="模块")
    environment = serializers.CharField(help_text="环境")
    bk_app_secret = SecretField(help_text="密钥")
    latest_deployed_at = serializers.DateTimeField(help_text="最近部署时间")


class AppSecretInEnvVarSLZ(serializers.Serializer):
    app_secret_in_config_var = SecretField(help_text="环境变量默认密钥")
    deployed_secret_list = serializers.ListField(child=DeployedSecretSLZ())
