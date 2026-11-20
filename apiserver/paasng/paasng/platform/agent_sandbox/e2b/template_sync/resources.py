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

"""集群里模板 CR 的增删查"""

import logging

from paas_wl.bk_app.agent_sandbox.constants import SANDBOX_INSTANCE_API_VERSION
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.base.base import EnhancedApiClient
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paasng.platform.agent_sandbox.models import E2BSandboxTemplate

from .manifests import build_pool_manifest, build_template_manifest, build_template_patch, is_managed, managed_labels

logger = logging.getLogger(__name__)


class TemplateResources:
    """单个集群命名空间内、由平台管理的模板 CR：每个模板对应同名的一个 SandboxTemplate 与一个 SandboxPool。

    只操作集群，不读库、不写下发状态
    """

    def __init__(self, client: EnhancedApiClient, namespace: str):
        self.client = client
        self.namespace = namespace

    def apply(self, template: E2BSandboxTemplate) -> None:
        """创建或更新模板的 CR。先模板后池子，池子引用的模板必须先存在"""
        name = template.resource_name
        self._create_or_patch(
            self._kres(kres.KSandboxTemplate),
            name,
            manifest=build_template_manifest(template, self.namespace),
            patch=build_template_patch(template, self.namespace),
        )
        pool = build_pool_manifest(template, self.namespace)
        self._create_or_patch(self._kres(kres.KSandboxPool), name, manifest=pool, patch=pool)

    def delete(self, resource_name: str) -> bool:
        """删除平台管理的同名 CR，先池子后模板。不带平台标签的 CR 原样保留。

        :returns: 是否删除了任何 CR
        """
        deleted = False
        for kres_cls in (kres.KSandboxPool, kres.KSandboxTemplate):
            res = self._kres(kres_cls)
            try:
                obj = res.get(resource_name, namespace=self.namespace)
            except ResourceMissing:
                continue
            if not is_managed(obj.to_dict()):
                logger.warning(
                    "%s %s/%s is not managed by platform, skip deleting", kres_cls.kind, self.namespace, resource_name
                )
                continue
            res.delete(resource_name, namespace=self.namespace)
            deleted = True
        return deleted

    def list_managed(self) -> set[str]:
        """列出平台管理的 CR 的资源名，池子与模板只要有一个在就算"""
        selector = managed_labels()
        return {
            item.metadata.name
            for kres_cls in (kres.KSandboxPool, kres.KSandboxTemplate)
            for item in self._kres(kres_cls).ops_batch.list(labels=selector, namespace=self.namespace).items
        }

    def _create_or_patch(self, res: kres.BaseKresource, name: str, manifest: dict, patch: dict) -> None:
        """不存在时按清单创建，已存在时以 merge patch 更新。

        不用 replace：整体覆盖会清掉控制器写在对象上的 finalizers、annotations 等元数据
        """
        try:
            res.get(name, namespace=self.namespace)
        except ResourceMissing:
            res.create(name, body=manifest, namespace=self.namespace)
        else:
            res.patch(name, body=patch, namespace=self.namespace, ptype=kres.PatchType.MERGE)

    def _kres(self, kres_cls: type[kres.BaseKresource]) -> kres.BaseKresource:
        return kres_cls(self.client, api_version=SANDBOX_INSTANCE_API_VERSION)
