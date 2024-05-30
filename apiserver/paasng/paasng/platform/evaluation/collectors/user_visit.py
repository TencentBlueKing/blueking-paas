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
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict

from paasng.accessories.paas_analysis.clients import SiteMetricsClient
from paasng.accessories.paas_analysis.constants import MetricSourceType
from paasng.accessories.paas_analysis.services import get_or_create_site_by_env
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


@dataclass
class EnvSummary:
    """环境资源使用数据"""

    pv: int
    uv: int


@dataclass
class ModuleSummary:
    """模块资源使用数据"""

    envs: Dict[str, EnvSummary]


@dataclass
class AppSummary:
    """应用资源使用数据"""

    app_code: str
    app_type: str
    time_range: str
    modules: Dict[str, ModuleSummary]


class AppUserVisitCollector:
    """应用访问数据采集器"""

    def __init__(self, app: Application, days: int = 30):
        self.app = app
        self.days = days

    def collect(self) -> AppSummary:
        module_summaries = {module.name: self._calc_module_summary(module) for module in self.app.modules.all()}
        return AppSummary(
            app_code=self.app.code, app_type=self.app.type, time_range=f"{self.days}d", modules=module_summaries
        )

    def _calc_module_summary(self, module: Module) -> ModuleSummary:
        stag_env = module.get_envs(AppEnvName.STAG)
        prod_env = module.get_envs(AppEnvName.PROD)
        return ModuleSummary(envs={env.environment: self._calc_env_pv_uv(env) for env in [stag_env, prod_env]})

    def _calc_env_pv_uv(self, env: ModuleEnvironment) -> EnvSummary:
        pv, uv = 0, 0
        today = date.today()
        try:
            client = SiteMetricsClient(get_or_create_site_by_env(env), MetricSourceType.INGRESS)
            resp = client.get_total_page_view_metric_about_site(today - timedelta(days=self.days), today)
            pv = resp["result"]["results"]["pv"]
            uv = resp["result"]["results"]["uv"]
        except Exception:
            logger.exception(
                "failed to get app %s module %s env %s pv & uv",
                env.application.code,
                env.module.name,
                env.environment,
            )

        return EnvSummary(pv=pv, uv=uv)
