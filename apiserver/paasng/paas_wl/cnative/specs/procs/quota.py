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

from paas_wl.cnative.specs.constants import LEGACY_PROC_RES_ANNO_KEY, PLAN_TO_QUOTA_MAP, ApiVersion, ResQuotaPlan
from paas_wl.cnative.specs.crd.bk_app import DEFAULT_PROC_CPU, DEFAULT_PROC_MEM, BkAppResource

logger = logging.getLogger(__name__)


class ResourceQuotaReader:
    """Read ResourceQuota (limit) from app model resource object

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self) -> Dict[str, Dict[str, str]]:
        """Read all resource quota defined

        :returns: A dict contains resource limit for all processes, value format: {"cpu": "1000m", "memory": "128Mi"}
        """
        if self.res.apiVersion == ApiVersion.V1ALPHA2:
            return self.from_v1alpha2_bkapp()

        if self.res.apiVersion == ApiVersion.V1ALPHA1:
            return self.from_v1alpha1_bkapp()

        raise ValueError(f"Unsupported api version: {self.res.apiVersion}")

    def from_v1alpha2_bkapp(self) -> Dict[str, Dict[str, str]]:
        # legacyProcResConfig 优先级更高
        if LEGACY_PROC_RES_ANNO_KEY in self.res.metadata.annotations:
            return json.loads(self.res.metadata.annotations[LEGACY_PROC_RES_ANNO_KEY])

        # 根据资源配额方案, 获取每个进程的配额
        return {p.name: self._get_quota_by_plan(p.resQuotaPlan) for p in self.res.spec.processes}  # type: ignore

    @staticmethod
    def _get_quota_by_plan(res_quota_plan: ResQuotaPlan) -> Dict[str, str]:
        cpu, mem = PLAN_TO_QUOTA_MAP.get(res_quota_plan, (DEFAULT_PROC_CPU, DEFAULT_PROC_MEM))
        return {"cpu": cpu, "memory": mem}

    def from_v1alpha1_bkapp(self) -> Dict[str, Dict[str, str]]:
        return {p.name: {"cpu": p.cpu, "memory": p.memory} for p in self.res.spec.processes}
