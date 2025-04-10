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

from typing import List

from rest_framework import serializers

from paas_wl.infras.cluster.constants import ClusterType
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.serializers import IngressConfigSLZ
from paas_wl.workloads.networking.egress.models import RegionClusterState
from paasng.platform.modules.constants import ExposedURLType


class APIServerSLZ(serializers.Serializer):
    uuid = serializers.CharField(required=False)
    host = serializers.CharField()


class ReadonlyClusterSLZ(serializers.Serializer):
    """Serializer for Cluster object"""

    uuid = serializers.CharField()
    name = serializers.CharField()
    type = serializers.ChoiceField(choices=ClusterType.get_choices())
    description = serializers.CharField()

    exposed_url_type = serializers.ChoiceField(choices=ExposedURLType.get_choices())
    ingress_config = IngressConfigSLZ()
    annotations = serializers.JSONField()

    ca_data = serializers.CharField()
    cert_data = serializers.CharField()
    key_data = serializers.CharField()
    token_value = serializers.CharField()

    default_node_selector = serializers.JSONField()
    default_tolerations = serializers.JSONField()
    feature_flags = serializers.JSONField()

    api_servers = APIServerSLZ(many=True)
    nodes = serializers.SerializerMethodField()

    def get_nodes(self, obj: Cluster) -> List[str]:
        """获取集群拥有的 Node 信息（根据 RegionClusterState 表查询，若有新增节点需要先更新状态）"""
        state = RegionClusterState.objects.filter(cluster_name=obj.name).first()
        if not state:
            return []
        return state.nodes_name


class GetClusterComponentStatusSLZ(serializers.Serializer):
    """获取集群组件状态用序列化器"""

    namespace = serializers.CharField(help_text="Chart 部署的命名空间", max_length=64)
    secret_name = serializers.CharField(help_text="存储 Release 信息的 Secret 名称", max_length=64)
