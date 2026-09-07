# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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


class ResourceQuotaSLZ(serializers.Serializer):
    cpu = serializers.CharField()
    memory = serializers.CharField()


class ResQuotaPlanListInputSLZ(serializers.Serializer):
    """资源配额方案可选列表查询参数"""

    app_code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="应用 ID，传入后按可见范围过滤；不传则只返回全局可用的资源套餐方案",
    )


class ResQuotaPlanSLZ(serializers.Serializer):
    """Serializer for ResQuotaPlan option"""

    name = serializers.CharField(help_text="方案名称")
    request = ResourceQuotaSLZ(help_text="资源请求")
    limit = ResourceQuotaSLZ(help_text="资源限制")
