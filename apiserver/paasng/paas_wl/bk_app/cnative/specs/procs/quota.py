# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import json

from attrs import asdict, define

from paas_wl.bk_app.cnative.specs.constants import (
    DEFAULT_RES_QUOTA_PLAN_NAME,
    OVERRIDE_PROC_RES_ANNO_KEY,
    RES_QUOTA_PLANS_ANNO_KEY,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paasng.platform.engine.constants import AppEnvName


@define
class ResourceQuota:
    cpu: str
    memory: str


# Deprecated: compatible with old data, will be removed in the future
LEGACY_QUOTA_PLANS = {
    "default": {
        "limits": ResourceQuota(cpu="4000m", memory="1024Mi"),
        "requests": ResourceQuota(cpu="200m", memory="256Mi"),
    },
    "4C1G": {
        "limits": ResourceQuota(cpu="4000m", memory="1024Mi"),
        "requests": ResourceQuota(cpu="200m", memory="256Mi"),
    },
    "4C2G": {
        "limits": ResourceQuota(cpu="4000m", memory="2048Mi"),
        "requests": ResourceQuota(cpu="200m", memory="1024Mi"),
    },
    "4C4G": {
        "limits": ResourceQuota(cpu="4000m", memory="4096Mi"),
        "requests": ResourceQuota(cpu="200m", memory="2048Mi"),
    },
}


class ResQuotaReader:
    """Read resource quota plans and environment overlays from BkAppResource"""

    def __init__(self, res: BkAppResource):
        self.res = res
        self._active_plans: dict[str, dict] = self._load_active_plans()

    def read_all(self, env_name: AppEnvName) -> dict[str, dict]:
        """Read all resource quota configs for given environment

        Note: OVERRIDE_PROC_RES_ANNO_KEY Annotation overrides have highest priority

        :param env_name: Environment name
        :return: {process_name: {plan: str, limits: {cpu, memory}, requests: {cpu, memory}}}
        """
        results: dict[str, dict] = {}

        for p in self.res.spec.processes:
            # if no plan is specified, use the default plan
            plan_name = p.resQuotaPlan or DEFAULT_RES_QUOTA_PLAN_NAME
            results[p.name] = self._get_plan_quota(plan_name)

        quotas_overlay = self.res.spec.envOverlay.resQuotas if self.res.spec.envOverlay else []
        for quotas in quotas_overlay or []:
            if quotas.envName == env_name:
                results[quotas.process] = self._get_plan_quota(quotas.plan)

        # structure: {process_name: {limits: {...}, requests: {...}}}
        override_str = self.res.metadata.annotations.get(OVERRIDE_PROC_RES_ANNO_KEY, "")
        if not override_str:
            return results

        override_map: dict[str, dict] = json.loads(override_str)
        for proc_name, config in results.items():
            if override_res := override_map.get(proc_name):
                if "limits" in override_res:
                    config["limits"] = override_res["limits"]
                if "requests" in override_res:
                    config["requests"] = override_res["requests"]

        return results

    def _get_plan_quota(self, plan_name: str) -> dict:
        """Get quota config by plan name (annotation plans > legacy plans)"""
        if plan_name in self._active_plans:
            plan = self._active_plans[plan_name]
            return {"plan": plan_name, "limits": plan["limits"], "requests": plan["requests"]}

        # Fallback to legacy plans
        legacy_plan = LEGACY_QUOTA_PLANS[plan_name]
        return {
            "plan": plan_name,
            "limits": asdict(legacy_plan["limits"]),
            "requests": asdict(legacy_plan["requests"]),
        }

    def _load_active_plans(self) -> dict[str, dict]:
        """Load active plans from annotations"""
        # structure: {plan_name: {limits: {...}, requests: {...}}}
        plans_str = self.res.metadata.annotations.get(RES_QUOTA_PLANS_ANNO_KEY, "")
        return json.loads(plans_str) if plans_str else {}
