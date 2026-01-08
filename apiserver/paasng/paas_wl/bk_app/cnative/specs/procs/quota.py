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

from paas_wl.bk_app.cnative.specs.constants import DEFAULT_RES_QUOTA_PLAN_NAME, OVERRIDE_PROC_RES_ANNO_KEY
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.procs.res_quota import get_active_res_quota_plans
from paasng.platform.engine.constants import AppEnvName


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
        active_plans = get_active_res_quota_plans()

        for p in self.res.spec.processes:
            # 如果未指定方案，使用 default 方案
            plan_name = p.resQuotaPlan or DEFAULT_RES_QUOTA_PLAN_NAME
            plan_obj = active_plans[plan_name]
            results[p.name] = {
                "plan": plan_obj.name,
                "limits": plan_obj.limits,
                "requests": plan_obj.requests,
            }

        if overlay := self.res.spec.envOverlay:
            quotas_overlay = overlay.resQuotas or []
        else:
            quotas_overlay = []

        for quotas in quotas_overlay:
            plan_obj = active_plans[quotas.plan]
            if quotas.envName == env_name:
                results[quotas.process] = {
                    "plan": plan_obj.name,
                    "limits": plan_obj.limits,
                    "requests": plan_obj.requests,
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
