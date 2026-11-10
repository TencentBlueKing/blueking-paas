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

"""把平台的 e2b 沙箱模板以 CR 形式下发到启用了 e2b 的集群。

数据库是唯一的事实来源：每个模板对应集群里同名的一个 SandboxTemplate 与一个 SandboxPool，
网关把资源名当作 e2b 的 templateID。下发是幂等的 upsert，失败的集群只记录结果、不回滚，
由平台管理端的手动同步补齐。

平台下发的 CR 都带 managed-by 标签。删除与清理只动带标签的 CR，集群里手工创建的不受影响。
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from paas_wl.bk_app.agent_sandbox.constants import (
    SANDBOX_INSTANCE_API_VERSION,
    SANDBOX_INSTANCE_DESIRED_STATE_RUNNING,
    SANDBOX_INSTANCE_NETWORK_MODE,
    SANDBOX_INSTANCE_RUNTIME_CLASS_NAME,
)
from paas_wl.infras.cluster.models import ClusterE2BConfig
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.base import EnhancedApiClient, get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate, E2BSandboxTemplateSyncRecord

from .clusters import list_e2b_clusters
from .constants import (
    GATEWAY_TEMPLATE_LABEL,
    TEMPLATE_MANAGED_BY_LABEL,
    TEMPLATE_MANAGED_BY_VALUE,
    TEMPLATE_PVC_SIZE_RATIO,
    E2BTemplateSyncStatus,
)
from .exceptions import E2BClusterUnavailable

logger = logging.getLogger(__name__)


@dataclass
class ClusterSyncResult:
    """单个集群的同步结果

    :param synced: 下发成功的资源名
    :param failed: 下发失败的资源名到失败原因的映射
    :param pruned: 因数据库中已不存在而被清理的资源名
    :param error: 集群级别的失败（如连不上集群），非空时其余字段可能不完整
    """

    cluster_name: str
    synced: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    pruned: list[str] = field(default_factory=list)
    error: str = ""


def build_template_manifest(template: E2BSandboxTemplate, namespace: str) -> dict[str, Any]:
    """生成模板对应的 SandboxTemplate"""
    name = template.resource_name
    container: dict[str, Any] = {"name": "main", "image": template.image, "imagePullPolicy": "IfNotPresent"}
    if template.env_vars:
        container["env"] = [{"name": k, "value": v} for k, v in sorted(template.env_vars.items())]
    if template.workdir:
        container["workingDir"] = template.workdir

    spec: dict[str, Any] = {
        "desiredState": SANDBOX_INSTANCE_DESIRED_STATE_RUNNING,
        "runtimeClassName": SANDBOX_INSTANCE_RUNTIME_CLASS_NAME,
        "network": {"mode": SANDBOX_INSTANCE_NETWORK_MODE},
        "domain": {"cpu": {"cores": template.cpu_count}, "memory": f"{template.memory_mb}Mi"},
        "podTemplate": {"containers": [container]},
        "retention": {"pod": "Delete", "pvc": "Delete", "dataVolume": "Delete"},
    }
    if template.disk_size_mb:
        _add_rootfs_disk(spec, template.disk_size_mb)

    return {
        "apiVersion": SANDBOX_INSTANCE_API_VERSION,
        "kind": "SandboxTemplate",
        "metadata": {"name": name, "namespace": namespace, "labels": _managed_labels()},
        "spec": {
            "template": {
                # 预热实例创建时就带上，网关据此回填 templateID
                "metadata": {"labels": {GATEWAY_TEMPLATE_LABEL: name}},
                "spec": spec,
            }
        },
    }


def _add_rootfs_disk(spec: dict[str, Any], disk_size_mb: int) -> None:
    """系统盘以盘镜像文件的形式放在每个沙箱独占的 PVC 上，PVC 要给文件系统开销留余量。

    布局与网关示例一致：盘镜像文件放在 PVC 的 rootfs 目录下
    """
    volume_name, pvc_name = "state", "state-pvc"
    pvc_size_mb = math.ceil(disk_size_mb * TEMPLATE_PVC_SIZE_RATIO)
    spec["domain"]["devices"] = {
        "disks": [
            {
                "name": "rootdisk",
                "role": "rootfsDisk",
                "volumeName": volume_name,
                "sourcePath": "rootfs",
                "image": "rootdisk.img",
                "fsType": "ext4",
                "size": f"{disk_size_mb}Mi",
            }
        ]
    }
    spec["podTemplate"]["volumes"] = [{"name": volume_name, "persistentVolumeClaim": {"claimName": pvc_name}}]
    spec["volumeClaimTemplates"] = [
        {
            "metadata": {"name": pvc_name},
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": settings.AGENT_SANDBOX_E2B_TEMPLATE_STORAGE_CLASS,
                "resources": {"requests": {"storage": f"{pvc_size_mb}Mi"}},
            },
        }
    ]


def build_pool_manifest(template: E2BSandboxTemplate, namespace: str) -> dict[str, Any]:
    """生成模板对应的 SandboxPool。自定义模板不预热，靠网关在无库存时现场创建"""
    replicas = template.prewarm_count if template.is_builtin else 0
    return {
        "apiVersion": SANDBOX_INSTANCE_API_VERSION,
        "kind": "SandboxPool",
        "metadata": {"name": template.resource_name, "namespace": namespace, "labels": _managed_labels()},
        "spec": {"replicas": replicas, "templateRef": {"name": template.resource_name}},
    }


@dataclass
class TemplateSyncOverview:
    """单个模板在各目标集群上的下发状态

    :param status: 汇总状态，任一集群失败即为失败，否则任一集群未完成即为待同步；没有目标集群时为空
    :param records: 各目标集群的下发记录
    :param missing: 是目标集群却没有记录的，多半是之后才启用 e2b、还没做过全量同步
    """

    template: E2BSandboxTemplate
    status: str | None
    records: list[E2BSandboxTemplateSyncRecord]
    missing: list[str]


@dataclass
class ClusterSyncOverview:
    """单个集群上各模板的下发状态，按资源名列出

    :param missing: 应当下发到该集群、却没有记录的模板
    """

    cluster_name: str
    namespace: str
    succeeded: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    @property
    def completed(self) -> bool:
        """应当下发到该集群的模板是否全部同步成功"""
        return not (self.pending or self.failed or self.missing)


def mark_pending(template: E2BSandboxTemplate) -> None:
    """模板保存后、下发前调用：目标集群全部置为待同步，不再是目标的集群的记录删除"""
    target_names = _TargetResolver(_enabled_cluster_names()).resolve(template)
    _reset_records(template, target_names)
    for cluster_name in target_names:
        _record(template, cluster_name, E2BTemplateSyncStatus.PENDING)


def sync_template(resource_name: str) -> None:
    """把单个模板的当前状态下发到它的目标集群，模板保存或删除后异步调用。

    模板已从数据库删除时，从所有启用 e2b 的集群里删掉它的 CR。
    """
    template = E2BSandboxTemplate.objects.filter(resource_name=resource_name).first()
    if template is None:
        for config in _enabled_configs():
            try:
                with get_client_by_cluster_name(config.cluster.name) as client:
                    _delete_managed(client, resource_name, config.namespace)
            except Exception:
                logger.exception(
                    "failed to delete e2b template %s from cluster %s", resource_name, config.cluster.name
                )
        return

    configs = _enabled_configs()
    # 目标集群可能在保存之后有变化，以下发时为准
    target_names = _TargetResolver({c.cluster.name for c in configs}).resolve(template)
    _reset_records(template, target_names)
    for config in configs:
        if config.cluster.name not in target_names:
            continue
        try:
            with get_client_by_cluster_name(config.cluster.name) as client:
                _apply(client, template, config.namespace)
        except Exception as exc:
            logger.exception("failed to sync e2b template %s to cluster %s", resource_name, config.cluster.name)
            _record(template, config.cluster.name, E2BTemplateSyncStatus.FAILED, str(exc))
        else:
            _record(template, config.cluster.name, E2BTemplateSyncStatus.SUCCEEDED)


def sync_all() -> list[ClusterSyncResult]:
    """把全部模板下发到全部启用 e2b 的集群，并清理数据库中已不存在的模板留下的 CR。

    所有模板的下发记录按本次结果重写。幂等，可重复调用。某个集群失败不影响其余集群。
    """
    templates = list(E2BSandboxTemplate.objects.select_related("application"))
    known_resource_names = {t.resource_name for t in templates}
    configs = _enabled_configs()
    resolver = _TargetResolver({c.cluster.name for c in configs})
    targets = {t.resource_name: resolver.resolve(t) for t in templates}
    for template in templates:
        _reset_records(template, targets[template.resource_name])

    results = []
    for config in configs:
        cluster_name = config.cluster.name
        result = ClusterSyncResult(cluster_name=cluster_name)
        results.append(result)
        cluster_templates = [t for t in templates if cluster_name in targets[t.resource_name]]
        try:
            with get_client_by_cluster_name(cluster_name) as client:
                for template in cluster_templates:
                    try:
                        _apply(client, template, config.namespace)
                    except Exception as exc:
                        logger.exception(
                            "failed to sync e2b template %s to cluster %s", template.resource_name, cluster_name
                        )
                        result.failed[template.resource_name] = _truncate(str(exc))
                        _record(template, cluster_name, E2BTemplateSyncStatus.FAILED, str(exc))
                    else:
                        result.synced.append(template.resource_name)
                        _record(template, cluster_name, E2BTemplateSyncStatus.SUCCEEDED)

                result.pruned = _prune(client, config.namespace, known_resource_names)
        except Exception as exc:
            logger.exception("failed to sync e2b templates to cluster %s", cluster_name)
            result.error = _truncate(str(exc))
            # 连不上集群时还没处理到的模板，同样记为失败，否则会残留成功或待同步的旧状态
            for template in cluster_templates:
                if template.resource_name not in result.synced and template.resource_name not in result.failed:
                    _record(template, cluster_name, E2BTemplateSyncStatus.FAILED, str(exc))
    return results


def get_template_overviews(templates: list[E2BSandboxTemplate]) -> list[TemplateSyncOverview]:
    """按模板汇总下发状态。模板须已 select_related("application") 与 prefetch_related("sync_records")"""
    resolver = _TargetResolver(_enabled_cluster_names())

    overviews = []
    for template in templates:
        target_names = resolver.resolve(template)
        records = [r for r in template.sync_records.all() if r.cluster_name in target_names]
        missing = sorted(target_names - {r.cluster_name for r in records})
        overviews.append(
            TemplateSyncOverview(
                template=template,
                status=_summarize({r.status for r in records}, has_missing=bool(missing)),
                records=records,
                missing=missing,
            )
        )
    return overviews


def get_cluster_overviews() -> list[ClusterSyncOverview]:
    """按集群汇总各模板的下发状态，覆盖全部启用 e2b 的集群"""
    configs = _enabled_configs()
    overviews = {
        c.cluster.name: ClusterSyncOverview(cluster_name=c.cluster.name, namespace=c.namespace) for c in configs
    }
    resolver = _TargetResolver(set(overviews))

    for template in E2BSandboxTemplate.objects.select_related("application").prefetch_related("sync_records"):
        records = {r.cluster_name: r for r in template.sync_records.all()}
        for cluster_name in resolver.resolve(template):
            overview = overviews[cluster_name]
            record = records.get(cluster_name)
            if record is None:
                overview.missing.append(template.resource_name)
            elif record.status == E2BTemplateSyncStatus.SUCCEEDED.value:
                overview.succeeded.append(template.resource_name)
            elif record.status == E2BTemplateSyncStatus.FAILED.value:
                overview.failed[template.resource_name] = record.message
            else:
                overview.pending.append(template.resource_name)
    return list(overviews.values())


def _enabled_configs() -> list[ClusterE2BConfig]:
    return list(ClusterE2BConfig.objects.select_related("cluster").filter(enabled=True))


def _enabled_cluster_names() -> set[str]:
    return set(ClusterE2BConfig.objects.filter(enabled=True).values_list("cluster__name", flat=True))


class _TargetResolver:
    """求模板应当下发到的集群：内置模板是全部启用 e2b 的集群，自定义模板只到应用租户可分配的那些。

    自定义模板的目标集群要走一遍集群分配，同一（租户, region）下的结果相同，实例内按此缓存，
    批量处理模板时复用同一个实例即可。

    :param enabled_names: 启用 e2b 的集群名
    """

    def __init__(self, enabled_e2b_clusters: set[str]):
        self._enabled_e2b_clusters = enabled_e2b_clusters
        self._allocated: dict[tuple[str, str], set[str]] = {}

    def resolve(self, template: E2BSandboxTemplate) -> set[str]:
        if template.is_builtin:
            return self._enabled_e2b_clusters

        app = template.application
        key = (app.tenant_id, app.region)
        if key not in self._allocated:
            try:
                names = set(list_e2b_clusters(app.tenant_id, app.region).values_list("name", flat=True))
            except E2BClusterUnavailable:
                logger.warning("no e2b cluster allocated for tenant %s, skip its custom templates", app.tenant_id)
                names = set()
            self._allocated[key] = names
        return self._allocated[key] & self._enabled_e2b_clusters


def _apply(client: EnhancedApiClient, template: E2BSandboxTemplate, namespace: str) -> None:
    """创建或覆盖模板的 CR。先模板后池子，池子引用的模板必须先存在"""
    name = template.resource_name
    _kres(kres.KSandboxTemplate, client).create_or_update(
        name,
        namespace=namespace,
        body=build_template_manifest(template, namespace),
        update_method="replace",
        auto_add_version=True,
    )
    _kres(kres.KSandboxPool, client).create_or_update(
        name,
        namespace=namespace,
        body=build_pool_manifest(template, namespace),
        update_method="replace",
        auto_add_version=True,
    )


def _delete_managed(client: EnhancedApiClient, resource_name: str, namespace: str) -> bool:
    """删除平台管理的同名 CR，先池子后模板。不带平台标签的 CR 原样保留。

    :returns: 是否删除了任何 CR
    """
    deleted = False
    for kres_cls in (kres.KSandboxPool, kres.KSandboxTemplate):
        res = _kres(kres_cls, client)
        try:
            obj = res.get(resource_name, namespace=namespace)
        except ResourceMissing:
            continue
        if not _is_managed(obj.to_dict()):
            logger.warning(
                "%s %s/%s is not managed by platform, skip deleting", kres_cls.kind, namespace, resource_name
            )
            continue
        res.delete(resource_name, namespace=namespace)
        deleted = True
    return deleted


def _prune(client: EnhancedApiClient, namespace: str, known_resource_names: set[str]) -> list[str]:
    """清理平台管理、但数据库中已不存在的模板留下的 CR"""
    selector = _managed_labels()
    stale: set[str] = set()
    for kres_cls in (kres.KSandboxPool, kres.KSandboxTemplate):
        for item in _kres(kres_cls, client).ops_batch.list(labels=selector, namespace=namespace).items:
            if item.metadata.name not in known_resource_names:
                stale.add(item.metadata.name)

    pruned = []
    for name in sorted(stale):
        if _delete_managed(client, name, namespace):
            pruned.append(name)
    return pruned


def _record(template: E2BSandboxTemplate, cluster_name: str, status: E2BTemplateSyncStatus, message: str = "") -> None:
    E2BSandboxTemplateSyncRecord.objects.update_or_create(
        template=template,
        cluster_name=cluster_name,
        defaults={"status": status.value, "message": _truncate(message)},
    )


def _reset_records(template: E2BSandboxTemplate, target_names: set[str]) -> None:
    """删掉不再是目标的集群的记录，如已停用 e2b 的集群"""
    E2BSandboxTemplateSyncRecord.objects.filter(template=template).exclude(cluster_name__in=target_names).delete()


def _summarize(statuses: set[str], has_missing: bool) -> str | None:
    if E2BTemplateSyncStatus.FAILED.value in statuses:
        return E2BTemplateSyncStatus.FAILED.value
    if has_missing or E2BTemplateSyncStatus.PENDING.value in statuses:
        return E2BTemplateSyncStatus.PENDING.value
    if statuses:
        return E2BTemplateSyncStatus.SUCCEEDED.value
    return None


def _kres(kres_cls: type[kres.BaseKresource], client: EnhancedApiClient) -> kres.BaseKresource:
    return kres_cls(client, api_version=SANDBOX_INSTANCE_API_VERSION)


def _managed_labels() -> dict[str, str]:
    return {TEMPLATE_MANAGED_BY_LABEL: TEMPLATE_MANAGED_BY_VALUE}


def _is_managed(manifest: dict[str, Any]) -> bool:
    labels = manifest.get("metadata", {}).get("labels") or {}
    return labels.get(TEMPLATE_MANAGED_BY_LABEL) == TEMPLATE_MANAGED_BY_VALUE


def _truncate(message: str) -> str:
    """失败原因入库、返回前截断，k8s 的报错可能带上整个响应体"""
    return message[:2000]
