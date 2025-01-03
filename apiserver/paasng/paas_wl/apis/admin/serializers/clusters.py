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

import base64
from typing import List

from rest_framework import serializers

from paas_wl.infras.cluster.constants import ClusterTokenType
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.serializers import IngressConfigSLZ
from paas_wl.workloads.networking.egress.models import RegionClusterState
from paasng.platform.modules.constants import ExposedURLType


def ensure_base64_encoded(content):
    try:
        base64.b64decode(content)
    except Exception:
        raise serializers.ValidationError("content is not a base64 encoded obj.")


class APIServerSLZ(serializers.Serializer):
    uuid = serializers.CharField(required=False, read_only=True)
    host = serializers.CharField()


class ReadonlyClusterSLZ(serializers.ModelSerializer):
    """Serializer for Cluster object"""

    ingress_config = IngressConfigSLZ(read_only=True)
    annotations = serializers.JSONField(read_only=True)
    api_servers = APIServerSLZ(many=True, read_only=True)
    default_node_selector = serializers.JSONField(read_only=True)
    default_tolerations = serializers.JSONField(read_only=True)
    feature_flags = serializers.JSONField(read_only=True)
    nodes = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Cluster
        fields = [
            "uuid",
            "region",
            "name",
            "type",
            "is_default",
            "description",
            "ingress_config",
            "annotations",
            "api_servers",
            # 相关证书
            "ca_data",
            "cert_data",
            "key_data",
            "token_value",
            "default_node_selector",
            "default_tolerations",
            "feature_flags",
            "nodes",
            "exposed_url_type",
        ]

    def get_nodes(self, obj: Cluster) -> List[str]:
        """获取集群拥有的 Node 信息（根据 RegionClusterState 表查询，若有新增节点需要先更新状态）"""
        state = RegionClusterState.objects.filter(cluster_name=obj.name).first()
        if not state:
            return []
        return state.nodes_name


class ClusterRegisterRequestSLZ(serializers.Serializer):
    """Serializer for registering Cluster"""

    name = serializers.CharField(required=True)
    region = serializers.CharField(required=True)
    type = serializers.CharField(required=True)
    is_default = serializers.BooleanField(required=False, default=False)
    # optional field
    description = serializers.CharField(required=False, default="")
    exposed_url_type = serializers.ChoiceField(choices=ExposedURLType.get_choices())
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
    feature_flags = serializers.JSONField(default=dict, required=False)


class GetClusterComponentStatusSLZ(serializers.Serializer):
    """获取集群组件状态用序列化器"""

    namespace = serializers.CharField(help_text="Chart 部署的命名空间", max_length=64)
    secret_name = serializers.CharField(help_text="存储 Release 信息的 Secret 名称", max_length=64)
