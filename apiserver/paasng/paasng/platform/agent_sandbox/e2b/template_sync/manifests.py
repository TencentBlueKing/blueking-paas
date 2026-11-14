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

"""由模板生成集群里的 CR 清单，以及判断集群里的 CR 是否已是当前配置所用的摘要。

平台下发的 CR 都带 managed-by 标签。删除与清理只动带标签的 CR，集群里手工创建的不受影响。
"""

import hashlib
import json
import math
from typing import Any

from django.conf import settings

from paas_wl.bk_app.agent_sandbox.constants import (
    SANDBOX_INSTANCE_API_VERSION,
    SANDBOX_INSTANCE_DESIRED_STATE_RUNNING,
    SANDBOX_INSTANCE_NETWORK_MODE,
    SANDBOX_INSTANCE_RUNTIME_CLASS_NAME,
)
from paasng.platform.agent_sandbox.e2b.constants import (
    GATEWAY_TEMPLATE_LABEL,
    TEMPLATE_MANAGED_BY_LABEL,
    TEMPLATE_MANAGED_BY_VALUE,
    TEMPLATE_PVC_SIZE_RATIO,
)
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate

# 决定沙箱规格的字段，即 SandboxTemplate 里来自模板的部分
SPEC_DIGEST_FIELDS = ("image", "cpu_count", "memory_mb", "disk_size_mb", "env_vars", "workdir")
# 会写进 CR 的全部模板字段，其余字段（名称、描述、启用、公开）只在平台内使用，改了不必重新下发
MANIFEST_FIELDS = (*SPEC_DIGEST_FIELDS, "prewarm_count")


def build_template_manifest(template: E2BSandboxTemplate, namespace: str) -> dict[str, Any]:
    """根据模板生成对应的 SandboxTemplate"""
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
        "metadata": {"name": name, "namespace": namespace, "labels": managed_labels()},
        "spec": {
            "template": {
                # 预热实例创建时就带上，底层 E2B 网关据此回填 templateID
                "metadata": {"labels": {GATEWAY_TEMPLATE_LABEL: name}},
                "spec": spec,
            }
        },
    }


def _add_rootfs_disk(spec: dict[str, Any], disk_size_mb: int) -> None:
    """系统盘以盘镜像文件的形式放在每个沙箱独占的 PVC 上"""
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
    """生成模板对应的 SandboxPool"""
    replicas = template.prewarm_count if template.is_builtin else 0
    return {
        "apiVersion": SANDBOX_INSTANCE_API_VERSION,
        "kind": "SandboxPool",
        "metadata": {"name": template.resource_name, "namespace": namespace, "labels": managed_labels()},
        "spec": {"replicas": replicas, "templateRef": {"name": template.resource_name}},
    }


def spec_digest(template: E2BSandboxTemplate) -> str:
    """模板当前规格的摘要，记录上的摘要与它相同且下发成功，即集群里的 SandboxTemplate 已是当前配置。

    只算模板字段，不算整份清单：平台生成清单的方式变了（标签、存储类等），集群里的旧 CR 照样能用，
    不该因此拦住所有创建。增删这里的字段会让全部记录对不上，上线后须做一次全量同步
    """
    spec = {f: getattr(template, f) for f in SPEC_DIGEST_FIELDS}
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def managed_labels() -> dict[str, str]:
    """平台下发的 CR 带的标签，也用作列出平台管理的 CR 的选择器"""
    return {TEMPLATE_MANAGED_BY_LABEL: TEMPLATE_MANAGED_BY_VALUE}


def is_managed(manifest: dict[str, Any]) -> bool:
    labels = manifest.get("metadata", {}).get("labels") or {}
    return labels.get(TEMPLATE_MANAGED_BY_LABEL) == TEMPLATE_MANAGED_BY_VALUE
