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
from paas_wl.infras.cluster.entities import AllocationRule, ManualAllocationConfig
from paas_wl.infras.cluster.models import Cluster


class EnvClustersSLZ(serializers.Serializer):
    """环境集群列表"""

    stag = serializers.ListField(help_text="预发布环境集群列表", child=serializers.CharField())
    prod = serializers.ListField(help_text="生产环境集群列表", child=serializers.CharField())


class ManualAllocationConfigSLZ(serializers.Serializer):
    """手动分配配置"""

    env_specific = serializers.BooleanField(help_text="是否按环境分配")
    clusters = serializers.ListField(
        help_text="集群列表（不区分环境）", child=serializers.CharField(), default=list, required=False
    )
    env_clusters = EnvClustersSLZ(help_text="环境集群列表", default=dict, required=False)

    def to_internal_value(self, data: Dict[str, Any]) -> ManualAllocationConfig:
        return ManualAllocationConfig(**super().to_internal_value(data))


class AllocationRuleSLZ(serializers.Serializer):
    """分配规则"""

    env_specific = serializers.BooleanField(help_text="是否按环境分配")
    matcher = serializers.DictField(help_text="匹配器", default=dict, required=False)
    clusters = serializers.ListField(
        help_text="集群列表（不区分环境）", child=serializers.CharField(), default=list, required=False
    )
    env_clusters = EnvClustersSLZ(help_text="环境集群列表", default=dict, required=False)

    def to_internal_value(self, data: Dict[str, Any]) -> AllocationRule:
        return AllocationRule(**super().to_internal_value(data))


class ClusterAllocationPolicyListOutputSLZ(serializers.Serializer):
    """集群分配策略列表"""

    id = serializers.UUIDField(help_text="分配策略 ID", source="uuid")
    tenant_id = serializers.CharField(help_text="所属租户")
    type = serializers.CharField(help_text="分配策略类型")
    manual_allocation_config = ManualAllocationConfigSLZ(help_text="手动分配配置")
    allocation_rules = serializers.ListField(help_text="分配规则列表", child=AllocationRuleSLZ())


def _validate_allocation_policy_clusters(
    tenant_id: str,
    manual_allocation_config: ManualAllocationConfig | None,
    allocation_rules: List[AllocationRule] | None,
) -> None:
    """校验配置的集群是否合法"""
    cluster_names = set()
    if manual_allocation_config:
        if clusters := manual_allocation_config.clusters:
            cluster_names |= set(clusters)
        if env_clusters := manual_allocation_config.env_clusters:
            for clusters in env_clusters.values():
                cluster_names |= set(clusters)

    if allocation_rules:
        # 遍历所有规则，获取使用到的集群名称
        for r in allocation_rules:
            if r.clusters:
                cluster_names |= set(r.clusters)
            if r.env_clusters:
                for clusters in r.env_clusters.values():
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
    manual_allocation_config = ManualAllocationConfigSLZ(help_text="手动分配配置", required=False)
    allocation_rules = serializers.ListField(help_text="分配规则列表", child=AllocationRuleSLZ(), required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        policy_type = attrs["type"]
        if policy_type == ClusterAllocationPolicyType.MANUAL:
            if not attrs.get("manual_allocation_config"):
                raise ValidationError(_("需要配置手动分配配置"))

            attrs["allocation_rules"] = []

        elif policy_type == ClusterAllocationPolicyType.RULE:
            if not attrs.get("allocation_rules"):
                raise ValidationError(_("需要配置分配规则"))

            attrs["manual_allocation_config"] = None

        _validate_allocation_policy_clusters(
            attrs["tenant_id"],
            attrs["manual_allocation_config"],
            attrs["allocation_rules"],
        )
        return attrs


class ClusterAllocationPolicyCreateOutputSLZ(serializers.Serializer):
    """创建集群分配策略"""

    id = serializers.CharField(help_text="分配策略 ID", source="uuid")


class ClusterAllocationPolicyUpdateInputSLZ(serializers.Serializer):
    """更新集群分配策略"""

    type = serializers.ChoiceField(help_text="分配策略类型", choices=ClusterAllocationPolicyType.get_choices())
    manual_allocation_config = ManualAllocationConfigSLZ(help_text="手动分配配置", required=False)
    allocation_rules = serializers.ListField(help_text="分配规则列表", child=AllocationRuleSLZ(), required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        policy_type = attrs["type"]
        if policy_type == ClusterAllocationPolicyType.MANUAL:
            if not attrs.get("manual_allocation_config"):
                raise ValidationError(_("需要配置手动分配配置"))

            attrs["allocation_rules"] = []

        elif policy_type == ClusterAllocationPolicyType.RULE:
            if not attrs.get("allocation_rules"):
                raise ValidationError(_("需要配置分配规则"))

            attrs["manual_allocation_config"] = None

        _validate_allocation_policy_clusters(
            self.context["cur_tenant_id"],
            attrs["manual_allocation_config"],
            attrs["allocation_rules"],
        )
        return attrs
