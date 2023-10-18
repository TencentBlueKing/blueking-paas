# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from typing import Tuple

from kubernetes.utils import parse_quantity

from paas_wl.bk_app.cnative.specs.constants import ApiVersion
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppBuildConfig, BkAppResource
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP
from paas_wl.workloads.release_controller.constants import ImagePullPolicy

logger = logging.getLogger(__name__)


class BkAppResourceConverter:
    """
    BkApp 版本转换器

    功能：尝试将 BkAppResource 转换成 v1alpha2 版本
    注意：当 BkApp 中使用多个不同镜像，则无法升到 v1alpha2 版本，但是资源配额转套餐不受影响
    """

    def __init__(self, bkapp: BkAppResource):
        self.bkapp = bkapp

    def convert(self) -> Tuple[BkAppResource, bool, bool]:
        """
        :returns: BkAppResource, converted, upgrade_version，分别对应转换后的 BkAppResource，是否发生转换，是否更新 apiVersion
        """
        # 如果已经是 v1alpha2 版本的 BkAppResource，直接跳过
        if self.bkapp.apiVersion == ApiVersion.V1ALPHA2:
            return self.bkapp, False, False

        upgrade_version = self._try_aggregate_images()
        self._convert_quota_to_plan()
        return self.bkapp, True, upgrade_version

    def _try_aggregate_images(self) -> bool:
        """尝试对使用的镜像进行聚合

        如果使用多个镜像，则不能进行聚合，以及升级到 v1alpha2 版本
        原因是尽管 v1alpha2 支持多镜像，但是基于注解的实现，前端交互并不支持
        :returns: upgrade_version 是否更新了 apiVersion
        """
        used_images = {p.image for p in self.bkapp.spec.processes if p.image}
        if len(used_images) != 1:
            logger.warning(f"BkAppResource {self.bkapp.metadata.name} has multiple images, cannot upgrade to v1alpha2")
            return False

        image_pull_policy = ImagePullPolicy.IF_NOT_PRESENT
        image_pull_policies = [p.imagePullPolicy for p in self.bkapp.spec.processes]

        # 如果有进程中的镜像拉取策略为 Always, 则将整个模块的策略设置为 Always
        if any(policy == ImagePullPolicy.ALWAYS for policy in image_pull_policies):
            image_pull_policy = ImagePullPolicy.ALWAYS

        # 进程中的镜像相关信息都设置为 None
        for p in self.bkapp.spec.processes:
            p.image = None
            p.imagePullPolicy = None

        # v1alpha2 仅保存镜像仓库，去掉 Tag
        repository, _, _ = used_images.pop().partition(":")
        self.bkapp.spec.build = BkAppBuildConfig(image=repository, imagePullPolicy=image_pull_policy)
        self.bkapp.apiVersion = ApiVersion.V1ALPHA2
        return True

    def _convert_quota_to_plan(self):
        """将资源配额转换成套餐

        resQuotaPlan 不受 bkApp 版本影响，可以直接转换（策略为向上取整），
        但是需要移除原有的 cpu，memory 配置，避免出现优先级覆盖问题
        """
        for p in self.bkapp.spec.processes:
            for plan, quota in PLAN_TO_LIMIT_QUOTA_MAP.items():
                if parse_quantity(p.cpu) <= parse_quantity(quota.cpu) and parse_quantity(p.memory) <= parse_quantity(
                    quota.memory
                ):
                    p.resQuotaPlan = plan
                    p.cpu, p.memory = "", ""
                    break
