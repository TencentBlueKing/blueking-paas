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
from collections import defaultdict
from typing import Dict, List

import cattr
import cryptography.x509
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.text import DNS_SAFE_PATTERN
from paas_wl.workloads.networking.ingress.kres_entities.service import PServicePortPair, service_kmodel
from paas_wl.workloads.networking.ingress.models import AppDomainSharedCert


class ProcServicePortSLZ(serializers.Serializer):
    name = serializers.RegexField(DNS_SAFE_PATTERN)
    protocol = serializers.CharField()
    port = serializers.IntegerField(min_value=1, max_value=65535)
    target_port = serializers.IntegerField(min_value=1, max_value=65535)

    def to_internal_value(self, data):
        return cattr.structure(data, PServicePortPair)


class ProcServiceSLZ(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    process_type = serializers.CharField(read_only=True)
    ports = ProcServicePortSLZ(many=True)

    def validate_ports(self, ports: List["PServicePortPair"]):
        if not ports:
            raise ValidationError(_("内部服务端口列表 ports 不能为空"))

        # Check if field values are duplicated
        seen_fields: Dict[str, set] = defaultdict(set)
        should_unique_fields = {"name", "port"}
        for port_pair in ports:
            for field in should_unique_fields:
                value = getattr(port_pair, field)
                if value in seen_fields[field]:
                    raise ValidationError(_("端口列表中发现重复值 {value}").format(value=value))

                seen_fields[field].add(value)
        return ports


class ProcIngressSLZ(serializers.Serializer):
    service_name = serializers.CharField(required=True)
    service_port_name = serializers.CharField(required=True)

    def _get_service(self, service_name):
        app = self.context["app"]
        try:
            return service_kmodel.get(app, service_name)
        except AppEntityNotFound:
            raise ValidationError(f"内部服务 {service_name} 不存在")

    def validate(self, data):
        port_name = data["service_port_name"]
        service = self._get_service(data["service_name"])
        if not any(port.name == port_name for port in service.ports):
            raise ValidationError(f"内部服务端口 {port_name} 不存在")
        return data


def validate_cert(d):
    """Validate certificate content"""
    try:
        cryptography.x509.load_pem_x509_certificate(bytes(d, "utf-8"))
    except ValueError:
        raise ValidationError("certificate is invalid, please check.")


class AppDomainSharedCertSLZ(serializers.ModelSerializer):
    cert_data = serializers.CharField(validators=[validate_cert], required=True)

    class Meta:
        model = AppDomainSharedCert
        exclude: List = []


class UpdateAppDomainSharedCertSLZ(serializers.ModelSerializer):
    """Serializer for updating shared cert object"""

    cert_data = serializers.CharField(validators=[validate_cert], required=True)

    class Meta:
        model = AppDomainSharedCert
        fields = ["cert_data", "key_data", "auto_match_cns"]
