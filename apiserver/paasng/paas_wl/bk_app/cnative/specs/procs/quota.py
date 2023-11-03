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
import json
import logging
from typing import Dict

import cattrs
from attrs import define

from paas_wl.bk_app.cnative.specs.constants import LEGACY_PROC_RES_ANNO_KEY, ApiVersion, ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import (
    DEFAULT_PROC_CPU,
    DEFAULT_PROC_CPU_REQUEST,
    DEFAULT_PROC_MEM,
    DEFAULT_PROC_MEM_REQUEST,
    BkAppResource,
)

logger = logging.getLogger(__name__)


@define
class ResourceQuota:
    cpu: str
    memory: str


# 资源配额方案到资源限制的映射表
PLAN_TO_LIMIT_QUOTA_MAP = {
    ResQuotaPlan.P_DEFAULT: ResourceQuota(
        cpu=DEFAULT_PROC_CPU,
        memory=DEFAULT_PROC_MEM,
    ),
    ResQuotaPlan.P_1C512M: ResourceQuota(cpu="1000m", memory="512Mi"),
    ResQuotaPlan.P_2C1G: ResourceQuota(cpu="2000m", memory="1024Mi"),
    ResQuotaPlan.P_2C2G: ResourceQuota(cpu="2000m", memory="2048Mi"),
    ResQuotaPlan.P_2C4G: ResourceQuota(cpu="2000m", memory="4096Mi"),
    ResQuotaPlan.P_4C1G: ResourceQuota(cpu="4000m", memory="1024Mi"),
    ResQuotaPlan.P_4C2G: ResourceQuota(cpu="4000m", memory="2048Mi"),
    ResQuotaPlan.P_4C4G: ResourceQuota(cpu="4000m", memory="4096Mi"),
}

# 资源配额方案到资源请求的映射表
# CPU REQUEST = CPU LIMIT / 4
# MEMORY REQUEST = MEMORY LIMIT / 2
PLAN_TO_REQUEST_QUOTA_MAP = {
    ResQuotaPlan.P_DEFAULT: ResourceQuota(
        cpu=DEFAULT_PROC_CPU_REQUEST,
        memory=DEFAULT_PROC_MEM_REQUEST,
    ),
    ResQuotaPlan.P_1C512M: ResourceQuota(cpu="256m", memory="256Mi"),
    ResQuotaPlan.P_2C1G: ResourceQuota(cpu="512m", memory="512Mi"),
    ResQuotaPlan.P_2C2G: ResourceQuota(cpu="512m", memory="1024Mi"),
    ResQuotaPlan.P_2C4G: ResourceQuota(cpu="512m", memory="2048Mi"),
    ResQuotaPlan.P_4C1G: ResourceQuota(cpu="1000m", memory="512Mi"),
    ResQuotaPlan.P_4C2G: ResourceQuota(cpu="1000m", memory="1024Mi"),
    ResQuotaPlan.P_4C4G: ResourceQuota(cpu="1000m", memory="2048Mi"),
}


class ResourceQuotaReader:
    """Read ResourceQuota (limit) from app model resource object

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self) -> Dict[str, ResourceQuota]:
        """Read all resource quota defined

        :returns: A dict contains resource limit for all processes, value format: {"cpu": "1000m", "memory": "128Mi"}
        """
        if self.res.apiVersion == ApiVersion.V1ALPHA2:
            return self.from_v1alpha2_bkapp()

        if self.res.apiVersion == ApiVersion.V1ALPHA1:
            return self.from_v1alpha1_bkapp()

        raise ValueError(f"Unsupported api version: {self.res.apiVersion}")

    def from_v1alpha2_bkapp(self) -> Dict[str, ResourceQuota]:
        # legacyProcResConfig 优先级更高
        if LEGACY_PROC_RES_ANNO_KEY in self.res.metadata.annotations:
            return cattrs.structure(
                json.loads(self.res.metadata.annotations[LEGACY_PROC_RES_ANNO_KEY]), Dict[str, ResourceQuota]
            )

        # 根据资源配额方案, 获取每个进程的配额
        return {
            p.name: PLAN_TO_LIMIT_QUOTA_MAP[p.resQuotaPlan or ResQuotaPlan.P_DEFAULT] for p in self.res.spec.processes
        }

    def from_v1alpha1_bkapp(self) -> Dict[str, ResourceQuota]:
        return {p.name: ResourceQuota(cpu=p.cpu or '', memory=p.memory or '') for p in self.res.spec.processes}
