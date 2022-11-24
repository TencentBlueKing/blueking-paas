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
from typing import Dict

from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers


class PortMapSLZ(serializers.Serializer):
    http = serializers.IntegerField(default=80, help_text="http 协议暴露端口")
    https = serializers.IntegerField(default=443, help_text="HTTPS 协议暴露端口")


class DomainSLZ(serializers.Serializer):
    name = serializers.CharField()
    reserved = serializers.NullBooleanField(default=False)
    https_enabled = serializers.NullBooleanField(default=False)

    class Meta:
        ref_name = "ingress_config.domain"


class IngressConfigSLZ(serializers.Serializer):
    """Serializer for IngressConfig object"""

    sub_path_domains = serializers.ListField(help_text="子路径根域名", child=DomainSLZ(), required=False, default=list)
    app_root_domains = serializers.ListField(help_text="子域名根域名", child=DomainSLZ(), required=False, default=list)
    frontend_ingress_ip = serializers.CharField(help_text="集群前置 IP", required=False, allow_blank=True)
    default_ingress_domain_tmpl = serializers.CharField(
        help_text="[Deprecated] 子路径渲染至 ingress 中的模板.", required=False, allow_null=True, allow_blank=True
    )
    port_map = PortMapSLZ(help_text="端口映射")

    def to_internal_value(self, data: Dict):
        data = super().to_internal_value(data)
        if not (data["sub_path_domains"] or data["app_root_domains"]):
            raise exceptions.ValidationError(_("`sub_path_domains` 与 `app_root_domains` 不能同时为空"))
        return data


class ClusterSLZ(serializers.Serializer):
    """Serializer for Cluster object"""

    name = serializers.CharField()
    is_default = serializers.BooleanField()
    bcs_cluster_id = serializers.CharField()
    support_bcs_metrics = serializers.BooleanField(default=False)
    ingress_config = IngressConfigSLZ()
