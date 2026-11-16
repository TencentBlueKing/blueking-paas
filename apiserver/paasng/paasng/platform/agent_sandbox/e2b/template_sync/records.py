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

"""维护各模板在各集群上的下发记录。

除下发本身外，模板保存、投递同步任务、集群下线时也要改记录，写记录的入口都在这里，读记录见 ``status``。
"""

from typing import Any

from paasng.platform.agent_sandbox.e2b.clusters import TemplateTargetResolver, list_enabled_e2b_cluster_names
from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate, E2BSandboxTemplateSyncRecord

from .manifests import spec_digest


def mark_pending(template: E2BSandboxTemplate) -> None:
    """模板保存后、下发前调用：目标集群全部置为待同步"""
    target_names = TemplateTargetResolver(list_enabled_e2b_cluster_names()).resolve(template)
    for cluster_name in target_names:
        record_status(template, cluster_name, E2BTemplateSyncStatus.PENDING)


def delete_cluster_records(cluster_name: str) -> None:
    """删掉该集群的全部下发记录。

    记录按集群名关联，不会随配置一起删除。留着的话，同名集群换了命名空间重新配置后，
    新命名空间里还没有 CR，旧记录却会让模板显示为可用
    """
    E2BSandboxTemplateSyncRecord.objects.filter(cluster_name=cluster_name).delete()


def record_status(
    template: E2BSandboxTemplate, cluster_name: str, status: E2BTemplateSyncStatus, message: str = ""
) -> None:
    """记录下发状态。下发完成（无论成败）时 template 须是刚下发的那份，摘要按它计算"""
    defaults: dict[str, Any] = {"status": status.value, "message": truncate_message(message)}
    if status != E2BTemplateSyncStatus.PENDING:
        defaults["digest"] = spec_digest(template)
    E2BSandboxTemplateSyncRecord.objects.update_or_create(
        template=template, cluster_name=cluster_name, defaults=defaults
    )


def prune_records(templates: list[E2BSandboxTemplate], targets: dict[str, set[str]]) -> None:
    """同步收尾时清理用不上的记录：模板在不再是目标的集群（如已停用 e2b）上的，以及模板已不存在的。

    读记录的地方都只看目标集群，留着不影响状态，清理只为不让记录越积越多

    :param targets: 资源名到目标集群的映射，须按全部启用 e2b 的集群求出
    """
    for template in templates:
        E2BSandboxTemplateSyncRecord.objects.filter(template=template).exclude(
            cluster_name__in=targets[template.resource_name]
        ).delete()
    # 模板删除时记录会级联删除，这里兜底绕过 ORM 删掉的
    E2BSandboxTemplateSyncRecord.objects.exclude(template_id__in=E2BSandboxTemplate.objects.values("pk")).delete()


def truncate_message(message: str) -> str:
    """失败原因入库、返回前截断，k8s 的报错可能带上整个响应体"""
    return message[:2000]
