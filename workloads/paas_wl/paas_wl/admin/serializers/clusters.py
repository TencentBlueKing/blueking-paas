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
import base64

from rest_framework import serializers

from paas_wl.cluster.constants import ClusterTokenType
from paas_wl.cluster.models import Cluster
from paas_wl.cluster.serializers import IngressConfigSLZ


def ensure_base64_encoded(content):
    try:
        base64.b64decode(content)
    except Exception:
        raise serializers.ValidationError("content is not a base64 encoded obj.")


class APIServerSLZ(serializers.Serializer):
    uuid = serializers.CharField(required=False, read_only=True)
    host = serializers.CharField()
    overridden_hostname = serializers.CharField(default=None, required=False, allow_blank=True)


class ReadonlyClusterSLZ(serializers.ModelSerializer):
    """Serializer for Cluster object"""

    ingress_config = IngressConfigSLZ(read_only=True)
    annotations = serializers.JSONField(read_only=True)
    api_servers = APIServerSLZ(many=True, read_only=True)
    default_node_selector = serializers.JSONField(read_only=True)
    default_tolerations = serializers.JSONField(read_only=True)

    class Meta:
        model = Cluster
        fields = [
            'uuid',
            'region',
            'name',
            'type',
            'is_default',
            'description',
            'ingress_config',
            'annotations',
            "api_servers",
            # 相关证书
            "ca_data",
            "cert_data",
            "key_data",
            "token_value",
            'default_node_selector',
            'default_tolerations',
        ]


class ClusterRegisterRequestSLZ(serializers.Serializer):
    """Serializer for registering Cluster"""

    name = serializers.CharField(required=True)
    region = serializers.CharField(required=True)
    is_default = serializers.BooleanField(required=False, default=False)
    # optional field
    description = serializers.CharField(required=False, default='')
    ingress_config = IngressConfigSLZ(required=False, default=None)
    annotations = serializers.JSONField(required=False, default=None)
    ca_data = serializers.CharField(
        validators=[ensure_base64_encoded], required=False, allow_blank=True, allow_null=True, default=None
    )
    cert_data = serializers.CharField(
        validators=[ensure_base64_encoded], required=False, allow_blank=True, allow_null=True, default=None
    )
    key_data = serializers.CharField(
        validators=[ensure_base64_encoded], required=False, allow_blank=True, allow_null=True, default=None
    )
    token_type = serializers.ChoiceField(choices=ClusterTokenType.get_django_choices(), required=False)
    token_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    default_node_selector = serializers.JSONField(default={}, required=False)
    default_tolerations = serializers.JSONField(default=[], required=False)
