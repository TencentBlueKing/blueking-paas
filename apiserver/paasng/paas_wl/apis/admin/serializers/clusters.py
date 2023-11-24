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
from typing import List

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.constants import ClusterTokenType
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.serializers import IngressConfigSLZ
from paas_wl.workloads.networking.egress.models import RegionClusterState


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
        ]

    def get_nodes(self, obj: Cluster) -> List[str]:
        """获取集群拥有的 Node 信息（根据 RegionClusterState 表查询，若有新增节点需要先更新状态）"""
        state = RegionClusterState.objects.filter(region=obj.region, cluster_name=obj.name).first()
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


class GenRegionClusterStateSLZ(serializers.Serializer):
    """生成 RegionClusterState 用序列化器"""

    region = serializers.CharField(required=True, help_text="specify a region name")
    ignore_labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="ignore nodes if it matches any of these labels, "
        "will always include 'node-role.kubernetes.io/master=true'",
    )
    include_masters = serializers.BooleanField(
        required=False, default=False, help_text="include master nodes or not, default is false"
    )

    def validate(self, attrs):
        cluster_regions = set(Cluster.objects.values_list("region", flat=True))

        # 若指定 region，则必须有对应 region 的集群
        if attrs["region"] not in cluster_regions:
            raise ValidationError(f"region: [{attrs['region']}] is not a valid region name")

        ignore_labels = [value.split("=") for value in attrs["ignore_labels"]]
        if any(len(label) != 2 for label in ignore_labels):
            raise ValidationError("invalid label given!")

        if not attrs["include_masters"]:
            ignore_labels.append(("node-role.kubernetes.io/master", "true"))

        attrs["ignore_labels"] = ignore_labels
        return attrs


class GetClusterComponentStatusSLZ(serializers.Serializer):
    """获取集群组件状态用序列化器"""

    namespace = serializers.CharField(help_text="Chart 部署的命名空间", max_length=64)
    secret_name = serializers.CharField(help_text="存储 Release 信息的 Secret 名称", max_length=64)
