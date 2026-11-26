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

"""根据配置一键初始化租户的集群、增强服务方案 / 资源池、绑定策略与日志配置"""

import json
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

from django.db import transaction
from django.db.models import Q

from paas_wl.infras.cluster.components import get_default_component_configs
from paas_wl.infras.cluster.constants import ClusterTokenType, ClusterType
from paas_wl.infras.cluster.models import (
    APIServer,
    Cluster,
    ClusterAllocationPolicy,
    ClusterAppImageRegistry,
    ClusterComponent,
    ClusterElasticSearchConfig,
)
from paas_wl.infras.resources.base.base import invalidate_global_configuration_pool
from paas_wl.workloads.networking.entrance.constants import AddressType
from paasng.accessories.log.models import TenantLogConfig
from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.local.manager import LocalServiceObj
from paasng.accessories.servicehub.manager import mixed_plan_mgr, mixed_service_mgr
from paasng.accessories.servicehub.services import NOTSET, PlanObj, ServiceObj
from paasng.accessories.services.models import Plan, PreCreatedInstance
from paasng.plat_mgt.infras.clusters.k8s import check_k8s_accessible
from paasng.plat_mgt.infras.services.serializers import PlanUpsertInputSLZ
from paasng.platform.modules.constants import ExposedURLType

if TYPE_CHECKING:
    from paas_wl.infras.cluster.entities import AllocationPolicy

logger = logging.getLogger(__name__)

ENV_REF_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand_env_refs(data: Any) -> Any:
    """将配置中所有字符串里的 ${NAME} 替换为环境变量的值

    :raises ValueError: 引用的环境变量不存在
    """
    missing: Set[str] = set()

    def _replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in os.environ:
            missing.add(name)
            return match.group(0)
        return os.environ[name]

    def _walk(value: Any) -> Any:
        if isinstance(value, str):
            return ENV_REF_PATTERN.sub(_replace, value)
        if isinstance(value, dict):
            return {k: _walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_walk(v) for v in value]
        return value

    result = _walk(data)
    if missing:
        raise ValueError(f"environment variables not set: {', '.join(sorted(missing))}")
    return result


class InitializationError(Exception):
    """预检失败，不会写入任何数据"""


class Action:
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"
    FAILED = "failed"


@dataclass
class Record:
    kind: str
    target: str
    action: str
    detail: str = ""


class TenantInfrasInitializer:
    """租户基础设施初始化

    执行顺序：预检（任一失败则不写入） -> 集群 -> 共享集群 -> 集群分配策略 -> 各增强服务 -> 日志配置。
    单个增强服务失败不影响其他服务，失败信息记录在 records 中，修正后重新执行即可补齐。

    :param data: 经 TenantInfrasSLZ 校验后的数据
    :param overwrite: 已存在的数据是否按配置更新，否则跳过
    :param dry_run: 只计算变更，不写入
    :param on_record: 每产生一条变更记录时的回调
    """

    def __init__(
        self,
        data: Dict[str, Any],
        overwrite: bool = False,
        dry_run: bool = True,
        on_record: Optional[Callable[[Record], None]] = None,
    ):
        self.data = data
        self.tenant_id: str = data["tenant_id"]
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.on_record = on_record
        self.records: List[Record] = []

    @property
    def failed_records(self) -> List[Record]:
        return [r for r in self.records if r.action == Action.FAILED]

    def run(self) -> List[Record]:
        services = self._preflight()

        self._init_clusters()
        self._init_shared_clusters()
        self._init_cluster_allocation_policy()
        for name, service in services.items():
            self._init_service_safely(name, service, self.data["services"][name])
        self._init_log_config()
        return self.records

    def _record(self, kind: str, target: str, action: str, detail: str = ""):
        record = Record(kind=kind, target=target, action=action, detail=detail)
        self.records.append(record)
        if self.on_record:
            self.on_record(record)

    def _should_write(self, kind: str, target: str, exists: bool) -> bool:
        """记录本项的变更动作，返回是否需要实际写入"""
        if exists and not self.overwrite:
            self._record(kind, target, Action.SKIP, "already exists")
            return False
        self._record(kind, target, Action.UPDATE if exists else Action.CREATE)
        return not self.dry_run

    # 预检

    def _preflight(self) -> Dict[str, ServiceObj]:
        for name in self.data["shared_clusters"]:
            if not Cluster.objects.filter(name=name).exists():
                raise InitializationError(f"shared cluster {name} does not exist")

        self._check_allocation_policy_clusters()
        services = {name: self._check_service(name, svc_data) for name, svc_data in self.data["services"].items()}

        for cluster_data in self.data["clusters"]:
            cluster = Cluster.objects.filter(name=cluster_data["name"]).first()
            removed = (
                set(cluster.available_tenant_ids) - set(cluster_data["available_tenant_ids"]) if cluster else set()
            )
            if self.overwrite and removed:
                raise InitializationError(
                    f"overwriting cluster {cluster_data['name']} would remove tenants {', '.join(sorted(removed))} "
                    "from its available tenants, please add them to available_tenant_ids"
                )
            if not self._cluster_needs_access_check(cluster, cluster_data):
                continue
            if not check_k8s_accessible(
                cluster_data["api_servers"],
                cluster_data["ca"],
                cluster_data["cert"],
                cluster_data["key"],
                cluster_data["token"],
            ):
                raise InitializationError(
                    f"cluster {cluster_data['name']} is not accessible, please check api servers and credentials"
                )
        return services

    def _check_allocation_policy_clusters(self):
        policy_data = self.data.get("cluster_allocation_policy")
        if not policy_data:
            return

        policies: List[AllocationPolicy] = [p.policy for p in policy_data["allocation_precedence_policies"]]
        if policy_data["allocation_policy"]:
            policies.append(policy_data["allocation_policy"])

        used_names: Set[str] = set()
        for policy in policies:
            used_names |= set(policy.clusters or [])
            for clusters in (policy.env_clusters or {}).values():
                used_names |= set(clusters)

        available_names = {c["name"] for c in self.data["clusters"]} | set(self.data["shared_clusters"])
        available_names |= set(
            Cluster.objects.filter(
                Q(tenant_id=self.tenant_id) | Q(available_tenant_ids__contains=self.tenant_id)
            ).values_list("name", flat=True)
        )
        if unknown := used_names - available_names:
            raise InitializationError(
                f"clusters {', '.join(sorted(unknown))} in allocation policy do not exist or are not available"
            )

    def _check_service(self, name: str, svc_data: Dict[str, Any]) -> ServiceObj:
        try:
            service = mixed_service_mgr.find_by_name(name, include_invisible=True)
        except ServiceObjNotFound:
            raise InitializationError(f"service {name} does not exist")

        if not _is_pool_service(service) and any(p["pre_created_instances"] for p in svc_data["plans"]):
            raise InitializationError(
                f"service {name} is not a resource pool service, pre_created_instances not allowed"
            )

        if policy := svc_data.get("binding_policy"):
            known = {p["name"] for p in svc_data["plans"]}
            known |= {p.name for p in service.get_plans_by_tenant_id(self.tenant_id, is_active=NOTSET)}
            if unknown := set(_policy_plan_names(policy)) - known:
                raise InitializationError(
                    f"plans {', '.join(sorted(unknown))} in binding policy of service {name} do not exist"
                )
        return service

    def _cluster_needs_access_check(self, cluster: Optional[Cluster], data: Dict[str, Any]) -> bool:
        if cluster is None:
            return True
        if not self.overwrite:
            return False
        auth_modified = (data["ca"], data["cert"], data["key"], data["token"]) != (
            cluster.ca_data,
            cluster.cert_data,
            cluster.key_data,
            cluster.token_value,
        )
        exists_api_servers = set(cluster.api_servers.values_list("host", flat=True))
        return auth_modified or exists_api_servers != set(data["api_servers"])

    # 集群

    def _init_clusters(self):
        modified = False
        for cluster_data in self.data["clusters"]:
            name = cluster_data["name"]
            cluster = Cluster.objects.filter(name=name).first()
            if not self._should_write("cluster", name, exists=cluster is not None):
                continue

            with transaction.atomic(using="workloads"):
                self._upsert_cluster(cluster, cluster_data)
            modified = True

        if modified:
            invalidate_global_configuration_pool()

    def _upsert_cluster(self, cluster: Optional[Cluster], data: Dict[str, Any]):
        created = cluster is None
        if cluster is None:
            cluster = Cluster(
                name=data["name"],
                tenant_id=self.tenant_id,
                type=ClusterType.NORMAL,
                token_type=ClusterTokenType.SERVICE_ACCOUNT,
            )

        cluster.available_tenant_ids = data["available_tenant_ids"]
        cluster.description = data["description"]
        cluster.exposed_url_type = (
            ExposedURLType.SUBPATH if data["app_address_type"] == AddressType.SUBPATH else ExposedURLType.SUBDOMAIN
        )
        cluster.ingress_config = data["ingress_config"]
        cluster.annotations = {**cluster.annotations, **data["annotations"]}
        cluster.ca_data = data["ca"]
        cluster.cert_data = data["cert"]
        cluster.key_data = data["key"]
        cluster.token_value = data["token"]
        cluster.default_tolerations = data["tolerations"]
        cluster.default_node_selector = data["node_selector"]
        cluster.container_log_dir = data["container_log_dir"]
        cluster.component_preferred_namespace = data["component_preferred_namespace"]
        cluster.component_image_registry = data["component_image_registry"]
        cluster.feature_flags = data["feature_flags"]
        cluster.save()

        cluster.api_servers.all().delete()
        APIServer.objects.bulk_create(
            [APIServer(cluster=cluster, host=host, tenant_id=cluster.tenant_id) for host in data["api_servers"]]
        )

        if created:
            ClusterComponent.objects.bulk_create(
                [
                    ClusterComponent(cluster=cluster, name=cfg["name"], required=cfg["required"])
                    for cfg in get_default_component_configs()
                ]
            )

        if es_cfg := data.get("elastic_search_config"):
            ClusterElasticSearchConfig.objects.update_or_create(
                cluster=cluster, tenant_id=cluster.tenant_id, defaults=es_cfg
            )
        else:
            ClusterElasticSearchConfig.objects.filter(cluster=cluster).delete()

        if image_registry := data.get("app_image_registry"):
            ClusterAppImageRegistry.objects.update_or_create(
                cluster=cluster, tenant_id=cluster.tenant_id, defaults=image_registry
            )
        else:
            ClusterAppImageRegistry.objects.filter(cluster=cluster).delete()

    def _init_shared_clusters(self):
        for name in self.data["shared_clusters"]:
            cluster = Cluster.objects.get(name=name)
            if self.tenant_id in cluster.available_tenant_ids:
                self._record("shared_cluster", name, Action.SKIP, "tenant already available")
                continue

            self._record("shared_cluster", name, Action.UPDATE, f"append {self.tenant_id} to available tenants")
            if self.dry_run:
                continue
            cluster.available_tenant_ids = [*cluster.available_tenant_ids, self.tenant_id]
            cluster.save(update_fields=["available_tenant_ids", "updated"])

    def _init_cluster_allocation_policy(self):
        data = self.data.get("cluster_allocation_policy")
        if not data:
            return

        policy = ClusterAllocationPolicy.objects.filter(tenant_id=self.tenant_id).first()
        if not self._should_write("cluster_allocation_policy", self.tenant_id, exists=policy is not None):
            return

        if policy:
            policy.type = data["type"]
            policy.allocation_policy = data["allocation_policy"]
            policy.allocation_precedence_policies = data["allocation_precedence_policies"]
            policy.save(update_fields=["type", "allocation_policy", "allocation_precedence_policies", "updated"])
        else:
            ClusterAllocationPolicy.objects.create(tenant_id=self.tenant_id, **data)

    # 增强服务

    def _init_service_safely(self, name: str, service: ServiceObj, svc_data: Dict[str, Any]):
        try:
            with transaction.atomic():
                self._init_service(service, svc_data)
        except Exception as e:
            logger.exception("failed to init service %s for tenant %s", name, self.tenant_id)
            self._record("service", name, Action.FAILED, str(e))

    def _init_service(self, service: ServiceObj, svc_data: Dict[str, Any]):
        for plan_data in svc_data["plans"]:
            self._upsert_plan(service, plan_data)

        # 远程服务的方案在 store 中刷新，需要重新获取服务对象
        service = mixed_service_mgr.get(service.uuid)
        if _is_pool_service(service):
            for plan_data in svc_data["plans"]:
                self._upsert_pre_created_instances(service, plan_data)

        self._init_binding_policy(service, svc_data)

    def _find_plan(self, service: ServiceObj, name: str) -> Optional[PlanObj]:
        plans = service.get_plans_by_tenant_id(self.tenant_id, is_active=NOTSET)
        return next((p for p in plans if p.name == name), None)

    def _upsert_plan(self, service: ServiceObj, plan_data: Dict[str, Any]):
        plan = self._find_plan(service, plan_data["name"])
        if not self._should_write("plan", f"{service.name}/{plan_data['name']}", exists=plan is not None):
            return

        slz = PlanUpsertInputSLZ(
            data={
                k: plan_data[k] for k in ("name", "description", "is_active", "config", "properties") if k in plan_data
            }
        )
        slz.is_valid(raise_exception=True)
        payload = slz.validated_data
        payload["tenant_id"] = self.tenant_id
        if plan:
            # 未声明的字段沿用当前值，避免被序列化器的默认值（空字典）覆盖
            for field in ("config", "properties"):
                if field not in plan_data:
                    payload[field] = getattr(plan, field)
            mixed_plan_mgr.update(service, plan_id=plan.uuid, plan_data=payload)
        else:
            mixed_plan_mgr.create(service, plan_data=payload)

    def _upsert_pre_created_instances(self, service: ServiceObj, plan_data: Dict[str, Any]):
        if not plan_data["pre_created_instances"]:
            return

        plan_obj = self._find_plan(service, plan_data["name"])
        plan = Plan.objects.get(uuid=plan_obj.uuid) if plan_obj else None
        existing = _group_instances_by_identity(plan) if plan else {}

        kind = "pre_created_instance"
        for idx, ins_data in enumerate(plan_data["pre_created_instances"]):
            identity = instance_identity(ins_data["credentials"])
            display = identity if "host" in ins_data["credentials"] else f"#{idx}"
            target = f"{service.name}/{plan_data['name']}/{display}"
            instances = existing.get(identity, [])
            # 只补足缺少的数量，多出的实例不会删除
            missing = ins_data["count"] - len(instances)
            fields = {
                "config": ins_data["config"],
                "credentials": json.dumps(ins_data["credentials"]),
                "allocation_type": ins_data["allocation_type"],
                "binding_policy": ins_data.get("binding_policy") or {},
            }

            if instances and self.overwrite:
                self._record(kind, target, Action.UPDATE, f"{len(instances)} instance(s)")
                if not self.dry_run:
                    for instance in instances:
                        for k, v in fields.items():
                            setattr(instance, k, v)
                        instance.save()

            if missing > 0:
                self._record(kind, target, Action.CREATE, f"{missing} instance(s)")
                if not self.dry_run:
                    assert plan is not None
                    for _ in range(missing):
                        PreCreatedInstance.objects.create(plan=plan, tenant_id=plan.tenant_id, **fields)
            elif not self.overwrite:
                self._record(kind, target, Action.SKIP, "already exists")

    def _init_binding_policy(self, service: ServiceObj, svc_data: Dict[str, Any]):
        mgr = SvcBindingPolicyManager(service, self.tenant_id)
        exists = mgr.get_comb_cfg() is not None
        if exists and not self.overwrite:
            self._record("binding_policy", service.name, Action.SKIP, "already exists")
            return

        policy = svc_data.get("binding_policy") or {"plans": [p["name"] for p in svc_data["plans"] if p["is_active"]]}
        if not _policy_plan_names(policy):
            return

        self._record("binding_policy", service.name, Action.UPDATE if exists else Action.CREATE)
        if self.dry_run:
            return

        name_to_id = {p.name: p.uuid for p in service.get_plans_by_tenant_id(self.tenant_id, is_active=NOTSET)}
        if plans := policy.get("plans"):
            mgr.set_uniform(plans=[name_to_id[n] for n in plans])
        else:
            env_plans = {env: [name_to_id[n] for n in names] for env, names in policy["env_plans"].items()}
            mgr.set_uniform(env_plans=env_plans)

    # 日志

    def _init_log_config(self):
        data = self.data.get("log_config")
        if not data:
            return

        exists = TenantLogConfig.objects.filter(tenant_id=self.tenant_id).exists()
        if not self._should_write("log_config", self.tenant_id, exists=exists):
            return

        defaults = dict(data)
        if exists and defaults.get("shared_bk_biz_id") is None:
            defaults.pop("shared_bk_biz_id", None)
            logger.info("shared_bk_biz_id not declared, keep current value of tenant %s", self.tenant_id)
        TenantLogConfig.objects.update_or_create(tenant_id=self.tenant_id, defaults=defaults)


def _is_pool_service(service: ServiceObj) -> bool:
    return isinstance(service, LocalServiceObj) and service.provider_name == "pool"


def _policy_plan_names(policy: Dict[str, Any]) -> List[str]:
    if plans := policy.get("plans"):
        return list(plans)
    return [n for names in (policy.get("env_plans") or {}).values() for n in names]


def _group_instances_by_identity(plan: Plan) -> Dict[str, List[PreCreatedInstance]]:
    groups: Dict[str, List[PreCreatedInstance]] = defaultdict(list)
    for ins in PreCreatedInstance.objects.filter(plan=plan):
        try:
            groups[instance_identity(json.loads(ins.credentials))].append(ins)
        except (TypeError, ValueError):
            logger.warning("invalid credentials of pre-created instance %s, ignored", ins.uuid)
    return groups


def instance_identity(credentials: Dict[str, Any]) -> str:
    """资源池实例以连接地址作为唯一标识，没有地址时使用完整凭证"""
    if "host" in credentials:
        return f"{credentials['host']}:{credentials.get('port', '')}"
    return json.dumps(credentials, sort_keys=True)
