# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyType
from paas_wl.infras.cluster.entities import IngressConfig
from paas_wl.infras.cluster.models import Cluster
from paasng.plat_admin.initialization.tenant_infras.initializer import instance_identity
from paasng.plat_mgt.infras.clusters.serializers import ClusterUpdateInputSLZ
from paasng.plat_mgt.infras.clusters.serializers.policies import AllocationPolicySLZ, AllocationPrecedencePolicySLZ
from paasng.plat_mgt.infras.services.serializers.pre_created_instances import PreCreatedInstanceUpsertSLZ


class TenantClusterSLZ(ClusterUpdateInputSLZ):
    """集群配置，字段与平台管理端的集群表单保持一致

    context 需要提供 cur_tenant_id（集群所属租户）与 cur_cluster（未入库的同名集群对象）
    """

    container_log_dir = serializers.CharField(help_text="容器日志目录", default="/var/lib/docker/containers")
    component_preferred_namespace = serializers.CharField(help_text="组件部署首选命名空间", default="blueking")
    component_image_registry = serializers.CharField(help_text="组件镜像仓库", default="hub.bktencent.com")

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        data = {"available_tenant_ids": [self.context["cur_tenant_id"]], **data}
        return super().to_internal_value(data)


def validate_clusters(tenant_id: str, clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """逐个校验集群配置（每个集群的校验上下文不同，无法使用嵌套序列化器）"""
    names = [c.get("name") for c in clusters]
    if len(names) != len(set(names)):
        raise ValidationError({"clusters": "集群名称不能重复"})

    results = []
    for idx, raw in enumerate(clusters):
        name = raw.get("name", "")
        cur_cluster = Cluster.objects.filter(name=name).first()
        if cur_cluster and cur_cluster.tenant_id != tenant_id:
            raise ValidationError(
                {"clusters": f"集群 {name} 已属于租户 {cur_cluster.tenant_id}，如需共享请配置在 shared_clusters 中"}
            )
        # 已存在的集群初始化时会跳过，其当前状态可能已在管理端变更，不再按配置校验
        if cur_cluster:
            results.append({"name": name})
            continue

        cur_cluster = Cluster(name=name, tenant_id=tenant_id, ingress_config=IngressConfig())
        slz = TenantClusterSLZ(data=raw, context={"cur_tenant_id": tenant_id, "cur_cluster": cur_cluster})
        if not slz.is_valid():
            raise ValidationError({"clusters": {idx: slz.errors}})
        results.append(slz.validated_data)
    return results


class ClusterAllocationPolicySLZ(serializers.Serializer):
    """集群分配策略，集群是否存在由初始化流程统一校验（可能引用本次新建的集群）"""

    type = serializers.ChoiceField(help_text="分配策略类型", choices=ClusterAllocationPolicyType.get_choices())
    allocation_policy = AllocationPolicySLZ(help_text="统一分配配置", required=False)
    allocation_precedence_policies = serializers.ListField(
        help_text="分配规则列表", child=AllocationPrecedencePolicySLZ(), max_length=20, required=False
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["type"] == ClusterAllocationPolicyType.UNIFORM:
            if not attrs.get("allocation_policy"):
                raise ValidationError("需要配置统一分配策略")
            attrs["allocation_precedence_policies"] = []
        else:
            policies = attrs.get("allocation_precedence_policies")
            if not policies or len(policies) < 2:
                raise ValidationError("至少配置两条分配规则")
            if policies[-1].matcher != {}:
                raise ValidationError("最后一条分配规则必须是 else 条件")
            attrs["allocation_policy"] = None
        return attrs


class PreCreatedInstanceSLZ(PreCreatedInstanceUpsertSLZ):
    credentials = serializers.DictField(help_text="预创建实例的凭据")
    count = serializers.IntegerField(
        help_text="实例数量，每条实例记录可分配给一个增强服务实例", min_value=1, default=1
    )


class PlanSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="方案名称", max_length=64)
    description = serializers.CharField(help_text="方案简介")
    is_active = serializers.BooleanField(help_text="是否可用", default=True)
    config = serializers.DictField(help_text="方案配置", required=False)
    properties = serializers.DictField(help_text="方案属性", required=False)
    pre_created_instances = PreCreatedInstanceSLZ(help_text="资源池实例，仅资源池类服务可用", many=True, default=list)

    def validate_pre_created_instances(self, instances: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # 同一实例出现多次时合并为一条，数量累加
        merged: dict[str, dict[str, Any]] = {}
        for ins in instances:
            identity = instance_identity(ins["credentials"])
            if identity in merged:
                merged[identity]["count"] += ins["count"]
            else:
                merged[identity] = ins
        return list(merged.values())


class EnvPlansSLZ(serializers.Serializer):
    stag = serializers.ListField(child=serializers.CharField(), min_length=1)
    prod = serializers.ListField(child=serializers.CharField(), min_length=1)


class ServiceBindingPolicySLZ(serializers.Serializer):
    """统一分配的绑定策略，方案均使用方案名称"""

    plans = serializers.ListField(help_text="方案名称列表", child=serializers.CharField(), required=False)
    env_plans = EnvPlansSLZ(help_text="按环境分配的方案名称", required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if bool(attrs.get("plans")) == bool(attrs.get("env_plans")):
            raise ValidationError("plans 与 env_plans 必须且只能配置一个")
        return attrs


class ServiceSLZ(serializers.Serializer):
    plans = PlanSLZ(help_text="方案列表", many=True, default=list)
    binding_policy = ServiceBindingPolicySLZ(help_text="绑定策略，默认统一分配本次声明的可用方案", required=False)

    def validate_plans(self, plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        names = [p["name"] for p in plans]
        if len(names) != len(set(names)):
            raise ValidationError("方案名称不能重复")
        return plans


class TenantLogConfigSLZ(serializers.Serializer):
    storage_cluster_id = serializers.IntegerField(help_text="日志平台存储集群 ID")
    retention = serializers.IntegerField(help_text="日志保存时间（天）", default=14)
    es_shards = serializers.IntegerField(help_text="ES 索引分片数", default=1)
    storage_replicas = serializers.IntegerField(help_text="存储副本数", default=1)
    time_zone = serializers.IntegerField(help_text="时区，如 8 表示 UTC+8", default=8)
    shared_bk_biz_id = serializers.IntegerField(
        help_text="平台级共享采集项所属的 bk_biz_id", default=None, allow_null=True
    )


class TenantInfrasSLZ(serializers.Serializer):
    """租户基础设施初始化配置"""

    tenant_id = serializers.CharField(help_text="租户 ID")
    clusters = serializers.ListField(help_text="新建的集群", child=serializers.DictField(), default=list)
    shared_clusters = serializers.ListField(
        help_text="已存在的集群，将本租户追加到其可用租户列表", child=serializers.CharField(), default=list
    )
    cluster_allocation_policy = ClusterAllocationPolicySLZ(help_text="集群分配策略", required=False)
    services = serializers.DictField(help_text="增强服务配置，key 为服务名称", child=ServiceSLZ(), default=dict)
    log_config = TenantLogConfigSLZ(help_text="租户日志配置", required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs["clusters"] = validate_clusters(attrs["tenant_id"], attrs["clusters"])

        declared = {c["name"] for c in attrs["clusters"]}
        if overlapped := declared & set(attrs["shared_clusters"]):
            raise ValidationError({"shared_clusters": f"集群 {', '.join(overlapped)} 不能同时出现在 clusters 中"})
        return attrs
