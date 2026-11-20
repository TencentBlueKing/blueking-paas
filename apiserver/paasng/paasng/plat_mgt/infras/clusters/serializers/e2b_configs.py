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

from typing import Any, Dict
from urllib.parse import urlparse

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class ClusterE2BConfigRetrieveOutputSLZ(serializers.Serializer):
    """集群 e2b 沙箱配置详情，api_key 只写不读"""

    control_plane_url = serializers.CharField(help_text="e2b-gateway 控制面地址")
    data_plane_address = serializers.CharField(help_text="供 SDK 直连的数据面对外地址")
    namespace = serializers.CharField(help_text="e2b 沙箱模板下发的命名空间")
    enabled = serializers.BooleanField(help_text="是否参与 e2b 沙箱调度")


class ClusterE2BConfigUpsertInputSLZ(serializers.Serializer):
    """新建或更新集群 e2b 沙箱配置"""

    control_plane_url = serializers.CharField(
        help_text="e2b-gateway 控制面地址，如 http://e2b-gateway.bcs-system:8080", max_length=256
    )
    # SDK 按 <端口>-<沙箱ID>.<data_plane_address> 拼主机名，因此只能是裸域名（可带端口）
    data_plane_address = serializers.RegexField(
        help_text="供 SDK 直连的数据面对外地址，填不带协议与路径的域名，如 e2b.example.com",
        regex=r"^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(:\d{1,5})?$",
        max_length=256,
        error_messages={"invalid": _("数据面地址须为不带协议与路径的域名，如 e2b.example.com")},
    )
    api_key = serializers.CharField(
        help_text="e2b-gateway 凭证，新建时必填；更新时留空表示沿用原值",
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    # 模板 CR 与存量沙箱都在原命名空间里，改了底层 E2B 网关就找不到它们，因此只能在新建时填写
    namespace = serializers.RegexField(
        help_text="e2b 沙箱模板下发的命名空间，须与底层 E2B 网关绑定的一致。新建时不填则为 default，创建后不能修改",
        regex=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
        max_length=63,
        required=False,
        error_messages={"invalid": _("命名空间须由小写字母、数字和 - 组成，且以字母或数字开头和结尾")},
    )
    enabled = serializers.BooleanField(help_text="是否参与 e2b 沙箱调度", default=True)

    def validate_control_plane_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"] or not parsed.netloc:
            raise ValidationError(_("控制面地址必须以 http 或 https 开头"))

        return url

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        cur_config = self.context.get("cur_config")
        if cur_config is not None and attrs.get("namespace", cur_config.namespace) != cur_config.namespace:
            raise ValidationError({"namespace": _("命名空间创建后不能修改，如需更换请先删除 e2b 沙箱配置再重新创建")})

        if attrs.get("api_key"):
            return attrs

        if cur_config is None:
            raise ValidationError({"api_key": _("新建 e2b 沙箱配置时，api_key 必须提供")})

        attrs.pop("api_key", None)
        return attrs
