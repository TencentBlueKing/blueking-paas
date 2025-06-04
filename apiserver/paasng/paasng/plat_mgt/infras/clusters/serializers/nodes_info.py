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

from rest_framework import serializers


# 节点信息序列化器
class ClusterNodesInfoListOutputSLZ(serializers.Serializer):
    nodes = serializers.ListField(child=serializers.CharField(), help_text="节点信息")
    binding_apps = serializers.ListField(child=serializers.CharField(), help_text="绑定应用")
    created_at = serializers.DateTimeField(help_text="同步时间")


class ClusterNodesInfoListInputSLZ(serializers.Serializer):
    cluster_name = serializers.CharField(help_text="集群名称", required=True)


# 节点同步记录序列化器
class ClusterNodesSyncInfoOutputSLZ(serializers.Serializer):
    nodes = serializers.ListField(child=serializers.CharField(), help_text="节点信息")
    binding_apps = serializers.ListField(child=serializers.CharField(), help_text="绑定应用")
    nodes_cnt = serializers.IntegerField(help_text="节点数")
    created_at = serializers.DateTimeField(help_text="同步时间")
