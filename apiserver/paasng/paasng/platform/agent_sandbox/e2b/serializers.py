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

from paasng.platform.agent_sandbox.models import E2BApiKey


class E2BApiKeyCreateInputSLZ(serializers.Serializer):
    name = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default="", help_text="便于区分多枚 key"
    )


class E2BApiKeyOutputSLZ(serializers.ModelSerializer):
    """key 的元信息。不含明文，明文只在签发响应里出现一次。

    不输出 ``enabled`` 与 ``revoked_at``：签发响应和列表都只涉及生效中的 key
    """

    class Meta:
        model = E2BApiKey
        fields = ["uuid", "name", "key_prefix", "created"]
        extra_kwargs = {
            "uuid": {"label": "密钥 ID"},
            "name": {"label": "名称"},
            "key_prefix": {"label": "密钥前缀"},
            "created": {"label": "签发时间"},
        }


class E2BApiKeyCreateOutputSLZ(E2BApiKeyOutputSLZ):
    """签发响应，比列表多一个明文字段。"""

    api_key = serializers.CharField(read_only=True, help_text="明文密钥，仅在本次响应中返回，请妥善保存")

    class Meta(E2BApiKeyOutputSLZ.Meta):
        fields = [*E2BApiKeyOutputSLZ.Meta.fields, "api_key"]
