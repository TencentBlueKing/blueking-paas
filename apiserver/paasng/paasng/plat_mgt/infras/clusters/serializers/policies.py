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

from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyType
from paas_wl.infras.cluster.entities import AllocationPolicy, AllocationPrecedencePolicy
from paas_wl.infras.cluster.models import Cluster


class EnvClustersSLZ(serializers.Serializer):
    """环境集群列表"""

    stag = serializers.ListField(help_text="预发布环境集群列表", child=serializers.CharField())
    prod = serializers.ListField(help_text="生产环境集群列表", child=serializers.CharField())


class AllocationPolicySLZ(serializers.Serializer):
    """统一分配策略"""

    env_specific = serializers.BooleanField(help_text="是否按环境分配")
    clusters = serializers.ListField(
        help_text="集群列表（不区分环境）", child=serializers.CharField(), default=list, required=False
    )
    env_clusters = EnvClustersSLZ(help_text="环境集群列表", default=dict, required=False)

    def to_internal_value(self, data: Dict[str, Any]) -> AllocationPolicy:
        return AllocationPolicy(**super().to_internal_value(data))


class AllocationPrecedencePolicySLZ(serializers.Serializer):
    """分配规则"""

    matcher = serializers.DictField(help_text="匹配器", default=dict)
    policy = AllocationPolicySLZ(help_text="分配策略")

    def to_internal_value(self, data: Dict[str, Any]) -> AllocationPrecedencePolicy:
        return AllocationPrecedencePolicy(**super().to_internal_value(data))


class ClusterAllocationPolicyListOutputSLZ(serializers.Serializer):
    """集群分配策略列表"""

    id = serializers.UUIDField(help_text="分配策略 ID", source="uuid")
    tenant_id = serializers.CharField(help_text="所属租户")
    type = serializers.ChoiceField(help_text="分配策略类型", choices=ClusterAllocationPolicyType.get_choices())
    allocation_policy = AllocationPolicySLZ(help_text="统一分配配置")
    allocation_precedence_policies = serializers.ListField(
        help_text="分配规则列表", child=AllocationPrecedencePolicySLZ()
    )


def _validate_allocation_policy_clusters(
    tenant_id: str,
    allocation_policy: AllocationPolicy | None,
    allocation_precedence_policies: List[AllocationPrecedencePolicy] | None,
) -> None:
    """校验配置的集群是否合法"""
    cluster_names = set()
    if allocation_policy:
        if clusters := allocation_policy.clusters:
            cluster_names |= set(clusters)
        if env_clusters := allocation_policy.env_clusters:
            for clusters in env_clusters.values():
                cluster_names |= set(clusters)

    if allocation_precedence_policies:
        # 遍历所有规则，获取使用到的集群名称
        for p in allocation_precedence_policies:
            if p.policy.clusters:
                cluster_names |= set(p.policy.clusters)
            if p.policy.env_clusters:
                for clusters in p.policy.env_clusters.values():
                    cluster_names |= set(clusters)

    # 校验集群是否存在 & 指定的租户可用
    exists_cluster_names = set(
        Cluster.objects.filter(available_tenant_ids__contains=tenant_id).values_list("name", flat=True)
    )
    if not_exists_cluster_names := (cluster_names - exists_cluster_names):
        raise ValidationError(_("集群名 {} 不存在或不可用").format(", ".join(not_exists_cluster_names)))


class ClusterAllocationPolicyCreateInputSLZ(serializers.Serializer):
    """创建集群分配策略"""

    tenant_id = serializers.CharField(help_text="所属租户")
    type = serializers.ChoiceField(help_text="分配策略类型", choices=ClusterAllocationPolicyType.get_choices())
    allocation_policy = AllocationPolicySLZ(help_text="手动分配配置", required=False)
    allocation_precedence_policies = serializers.ListField(
        help_text="分配规则列表", child=AllocationPrecedencePolicySLZ(), required=False
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        policy_type = attrs["type"]
        if policy_type == ClusterAllocationPolicyType.UNIFORM:
            if not attrs.get("allocation_policy"):
                raise ValidationError(_("需要配置统一分配策略"))

            attrs["allocation_precedence_policies"] = []

        elif policy_type == ClusterAllocationPolicyType.RULE_BASED:
            if not attrs.get("allocation_precedence_policies"):
                raise ValidationError(_("需要配置分配规则"))

            attrs["allocation_policy"] = None

        _validate_allocation_policy_clusters(
            attrs["tenant_id"],
            attrs["allocation_policy"],
            attrs["allocation_precedence_policies"],
        )
        return attrs


class ClusterAllocationPolicyCreateOutputSLZ(serializers.Serializer):
    """创建集群分配策略"""

    id = serializers.CharField(help_text="分配策略 ID", source="uuid")


class ClusterAllocationPolicyUpdateInputSLZ(serializers.Serializer):
    """更新集群分配策略"""

    type = serializers.ChoiceField(help_text="分配策略类型", choices=ClusterAllocationPolicyType.get_choices())
    allocation_policy = AllocationPolicySLZ(help_text="手动分配配置", required=False)
    allocation_precedence_policies = serializers.ListField(
        help_text="分配规则列表", child=AllocationPrecedencePolicySLZ(), required=False
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        policy_type = attrs["type"]
        if policy_type == ClusterAllocationPolicyType.UNIFORM:
            if not attrs.get("allocation_policy"):
                raise ValidationError(_("需要配置统一分配策略"))

            attrs["allocation_precedence_policies"] = []

        elif policy_type == ClusterAllocationPolicyType.RULE_BASED:
            if not attrs.get("allocation_precedence_policies"):
                raise ValidationError(_("需要配置分配规则"))

            attrs["allocation_policy"] = None

        _validate_allocation_policy_clusters(
            self.context["cur_tenant_id"],
            attrs["allocation_policy"],
            attrs["allocation_precedence_policies"],
        )
        return attrs
