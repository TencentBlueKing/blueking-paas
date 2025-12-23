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

from paas_wl.bk_app.cnative.specs.constants import OVERRIDE_PROC_RES_ANNO_KEY
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.models import ResQuotaPlan
from paasng.platform.engine.constants import AppEnvName


@define
class ResourceQuota:
    cpu: str
    memory: str


class ResQuotaReader:
    """Read resQuotaPlan and resQuotas(envOverlay) from app model resource object

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self, env_name: AppEnvName) -> dict[str, dict]:
        """Read all ResQuota config defined

        :param env_name: Environment name
        :return: Dict[name of process, config],
          config is {"plan": plan name, "limits": {"cpu":cpu limit, "memory": memory limit},
          "requests": {"cpu":cpu request, "memory": memory request}}

        Note: If override_proc_res is configured in BkAppResource's annotations,
          it will be applied with the highest priority.
        """
        results: dict[str, dict] = {}
        active_plans = {plan_obj.plan_name: plan_obj for plan_obj in ResQuotaPlan.objects.filter(is_active=True)}
        for p in self.res.spec.processes:
            plan_obj: ResQuotaPlan = active_plans.get(p.resQuotaPlan, active_plans["default"])
            results[p.name] = {
                "plan": plan_obj.plan_name,
                "limits": asdict(ResourceQuota(cpu=plan_obj.cpu_limit, memory=plan_obj.memory_limit)),
                # TODO 云原生应用的 requests 取值策略在 operator 中实现. 这里的值并非实际生效值, 仅用于前端展示. 如果需要, 后续校正?
                "requests": asdict(ResourceQuota(cpu=plan_obj.cpu_request, memory=plan_obj.memory_request)),
            }

        if overlay := self.res.spec.envOverlay:
            quotas_overlay = overlay.resQuotas or []
        else:
            quotas_overlay = []

        for quotas in quotas_overlay:
            if quotas.envName == env_name:
                plan_obj = active_plans[quotas.plan]
                results[quotas.process] = {
                    "plan": plan_obj.plan_name,
                    "limits": asdict(ResourceQuota(cpu=plan_obj.cpu_limit, memory=plan_obj.memory_limit)),
                    "requests": asdict(ResourceQuota(cpu=plan_obj.cpu_request, memory=plan_obj.memory_request)),
                }

        override_config_str = self.res.metadata.annotations.get(OVERRIDE_PROC_RES_ANNO_KEY, "")
        if not override_config_str:
            return results

        override_map = json.loads(override_config_str)
        for proc_name, config in results.items():
            if override_res := override_map.get(proc_name):
                if "limits" in override_res:
                    config["limits"] = override_res["limits"]
                if "requests" in override_res:
                    config["requests"] = override_res["requests"]

        return results
