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

from typing import Any, Dict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from paas_wl.infras.cluster.entities import AllocationRule
from paas_wl.infras.cluster.models import Cluster


class EnvClustersSLZ(serializers.Serializer):
    """环境集群列表"""

    stag = serializers.ListField(help_text="预发布环境集群列表", child=serializers.CharField())
    prod = serializers.ListField(help_text="生产环境集群列表", child=serializers.CharField())


class AllocationRuleSLZ(serializers.Serializer):
    """分配规则"""

    env_specific = serializers.BooleanField(help_text="是否按环境分配")
    matcher = serializers.DictField(help_text="匹配器")
    clusters = serializers.ListField(help_text="集群列表（不区分环境）", child=serializers.CharField())
    env_clusters = EnvClustersSLZ(help_text="环境集群列表")

    def to_internal_value(self, data: Dict[str, Any]) -> AllocationRule:
        return AllocationRule(**super().to_internal_value(data))


class ClusterAllocationPolicyListOutputSLZ(serializers.Serializer):
    """集群分配策略列表"""

    id = serializers.UUIDField(help_text="分配策略 ID")
    tenant_id = serializers.CharField(help_text="所属租户")
    type = serializers.CharField(help_text="分配策略类型")
    rules = serializers.ListField(help_text="分配规则列表", child=AllocationRuleSLZ())


class ClusterAllocationPolicyCreateInputSLZ(serializers.Serializer):
    """创建集群分配策略"""

    tenant_id = serializers.CharField(help_text="所属租户")
    type = serializers.CharField(help_text="分配策略类型")
    rules = serializers.ListField(help_text="分配规则列表", child=AllocationRuleSLZ(), min_length=1, max_length=10)


class ClusterAllocationPolicyCreateOutputSLZ(serializers.Serializer):
    """创建集群分配策略"""

    id = serializers.CharField(help_text="分配策略 ID")


class ClusterAllocationPolicyUpdateInputSLZ(serializers.Serializer):
    """创建集群分配策略"""

    type = serializers.CharField(help_text="分配策略类型")
    rules = serializers.ListField(help_text="分配规则列表", child=AllocationRuleSLZ(), min_length=1, max_length=10)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        # 校验规则是否为空
        if not attrs["rules"]:
            raise serializers.ValidationError(_("分配规则不能为空"))

        cluster_names = set()
        for rule in attrs["rules"]:
            cluster_names |= set(rule["clusters"])
            for env_clusters in rule["env_clusters"].values():
                cluster_names |= set(env_clusters)

        # 校验集群是否存在
        exists_cluster_names = set(Cluster.objects.values_list("name", flat=True))
        if not_exists_cluster_names := cluster_names - exists_cluster_names:
            raise serializers.ValidationError(_("集群名 {} 不存在").format(", ".join(not_exists_cluster_names)))

        return attrs
