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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paasng.platform.applications.models import AppCodeAuthCode


class GenAuthCodeInputSLZ(serializers.Serializer):
    """生成授权码的输入参数"""

    app_code = serializers.CharField(max_length=20, required=True, help_text="应用 ID")

    def validate_app_code(self, value):
        if AppCodeAuthCode.objects.filter(app_code=value).exists():
            raise serializers.ValidationError(_("应用 ID 已存在授权码"))
        return value


class AuthCodeOutputSLZ(serializers.Serializer):
    """Auth code output serializer"""

    id = serializers.CharField(help_text="授权码 ID")
    auth_code = serializers.CharField(help_text="授权码")
    app_code = serializers.CharField(help_text="应用 ID")
    is_used = serializers.BooleanField(help_text="是否已使用")
    created = serializers.DateTimeField(help_text="创建时间")


class AuthCodeListInputSLZ(serializers.Serializer):
    """Query params for listing auth codes"""

    search = serializers.CharField(required=False, allow_blank=True, default=None, help_text="搜索应用 ID 或授权码")
