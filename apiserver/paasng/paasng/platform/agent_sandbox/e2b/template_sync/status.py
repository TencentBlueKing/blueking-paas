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

"""根据各集群的下发状态汇总模板的同步情况

每个集群的下发状态只描述最近一次下发：结果，以及所下发配置的摘要。
"""

from dataclasses import dataclass, field
from typing import Sequence

from paasng.platform.agent_sandbox.e2b.clusters import (
    list_enabled_e2b_configs,
    resolve_template_targets,
    select_e2b_cluster,
)
from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateStatus, E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.exceptions import E2BClusterUnavailable
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate, E2BSandboxTemplateSyncState
from paasng.platform.applications.models import Application

from .manifests import spec_digest


@dataclass
class TemplateSyncOverview:
    """单个模板在各目标集群上的下发状态

    :param status: 汇总状态，任一集群失败即为失败，否则任一集群未完成即为待同步；没有目标集群时为空
    :param states: 各目标集群的下发状态。其中的 status 字段可能已过期，展示时以 ``get_sync_status`` 为准
    :param missing: 是目标集群却没有下发状态的，多半是之后才启用 e2b、还没做过全量同步
    """

    template: E2BSandboxTemplate
    status: str | None
    states: list[E2BSandboxTemplateSyncState]
    missing: list[str]


@dataclass
class ClusterSyncOverview:
    """单个集群上各模板的下发状态，按资源名列出"""

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


def get_template_overviews(templates: list[E2BSandboxTemplate]) -> list[TemplateSyncOverview]:
    """按模板汇总下发状态"""
    targets = resolve_template_targets(templates)

    overviews = []
    for template in templates:
        target_names = targets[template.resource_name]
        # 列出模板在目标集群上的下发状态
        states = [s for s in template.sync_states.all() if s.cluster_name in target_names]
        # 没有下发状态的集群标记为 missing
        missing = sorted(target_names - {s.cluster_name for s in states})
        overviews.append(
            TemplateSyncOverview(
                template=template,
                status=_summarize({get_sync_status(s, template) for s in states}, has_missing=bool(missing)),
                states=states,
                missing=missing,
            )
        )
    return overviews


def get_cluster_overviews() -> list[ClusterSyncOverview]:
    """按集群汇总各模板的下发状态，覆盖全部启用 e2b 的集群"""
    overviews = {
        c.cluster.name: ClusterSyncOverview(cluster_name=c.cluster.name, namespace=c.namespace)
        for c in list_enabled_e2b_configs()
    }
    templates = list(E2BSandboxTemplate.objects.select_related("application").prefetch_related("sync_states"))
    targets = resolve_template_targets(templates, set(overviews))

    for template in templates:
        states = {s.cluster_name: s for s in template.sync_states.all()}
        for cluster_name in targets[template.resource_name]:
            overview = overviews[cluster_name]
            state = states.get(cluster_name)
            if state is None:
                overview.missing.append(template.resource_name)
                continue

            sync_status = get_sync_status(state, template)
            if sync_status == E2BTemplateSyncStatus.SUCCEEDED:
                overview.succeeded.append(template.resource_name)
            elif sync_status == E2BTemplateSyncStatus.FAILED:
                overview.failed[template.resource_name] = state.message
            else:
                overview.pending.append(template.resource_name)
    return list(overviews.values())


def is_applied(template: E2BSandboxTemplate, cluster_name: str) -> bool:
    """集群里的 SandboxTemplate 是否已是模板的当前配置"""
    state = E2BSandboxTemplateSyncState.objects.filter(template=template, cluster_name=cluster_name).first()
    return state is not None and is_up_to_date(state, template)


def get_template_statuses(
    application: Application, templates: Sequence[E2BSandboxTemplate]
) -> dict[str, E2BTemplateStatus]:
    """应用视角下各模板能否用来创建沙箱，键为资源名。

    按应用当前的首选集群判断，与创建沙箱时的检查一致。首选集群会随分配策略变化，
    所以只反映此刻的结果
    """
    try:
        cluster_name = select_e2b_cluster(application.tenant_id, application.region).name
    except E2BClusterUnavailable:
        return {t.resource_name: E2BTemplateStatus.NO_CLUSTER for t in templates}

    states = {
        s.template_id: s
        for s in E2BSandboxTemplateSyncState.objects.filter(template__in=templates, cluster_name=cluster_name)
    }
    return {t.resource_name: _template_status(t, states.get(t.pk)) for t in templates}


def is_up_to_date(state: E2BSandboxTemplateSyncState, template: E2BSandboxTemplate) -> bool:
    """最近一次下发成功，且下发的就是模板当前配置"""
    return state.status == E2BTemplateSyncStatus.SUCCEEDED.value and state.digest == spec_digest(template)


def get_sync_status(state: E2BSandboxTemplateSyncState, template: E2BSandboxTemplate) -> E2BTemplateSyncStatus:
    """取有效的状态值，所有按下发状态做判断的地方都以它为准。

    成功但摘要与模板当前配置不一致的按待同步算：集群里不是当前配置，创建沙箱会被拦下。
    正常保存模板时状态会先被置为待同步，绕过 templates 直接改库、或改了参与摘要的字段时才会出现
    """
    if is_up_to_date(state, template):
        return E2BTemplateSyncStatus.SUCCEEDED
    if state.status == E2BTemplateSyncStatus.FAILED.value:
        return E2BTemplateSyncStatus.FAILED
    return E2BTemplateSyncStatus.PENDING


_TEMPLATE_STATUSES = {
    E2BTemplateSyncStatus.SUCCEEDED: E2BTemplateStatus.AVAILABLE,
    E2BTemplateSyncStatus.FAILED: E2BTemplateStatus.SYNC_FAILED,
    E2BTemplateSyncStatus.PENDING: E2BTemplateStatus.SYNCING,
}


def _template_status(template: E2BSandboxTemplate, state: E2BSandboxTemplateSyncState | None) -> E2BTemplateStatus:
    if state is None:
        return E2BTemplateStatus.SYNCING
    return _TEMPLATE_STATUSES[get_sync_status(state, template)]


def _summarize(statuses: set[E2BTemplateSyncStatus], has_missing: bool) -> str | None:
    if E2BTemplateSyncStatus.FAILED in statuses:
        return E2BTemplateSyncStatus.FAILED.value
    if has_missing or E2BTemplateSyncStatus.PENDING in statuses:
        return E2BTemplateSyncStatus.PENDING.value
    if statuses:
        return E2BTemplateSyncStatus.SUCCEEDED.value
    return None
