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
from datetime import datetime
from typing import Dict, Optional

from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models import Deployment
from paasng.platform.modules.models import Module
from paasng.utils.basic import get_username_by_bkpaas_user_id

logger = logging.getLogger(__name__)


@dataclass
class EnvSummary:
    """环境资源使用数据"""

    latest_deployer: Optional[str] = None
    latest_deployed_at: Optional[datetime] = None


@dataclass
class ModuleSummary:
    """模块资源使用数据"""

    envs: Dict[str, EnvSummary]


@dataclass
class AppSummary:
    """应用资源使用数据"""

    app_code: str
    app_type: str
    modules: Dict[str, ModuleSummary]


class AppDeploymentCollector:
    """应用资源历史使用数据采集器"""

    def __init__(self, app: Application):
        self.app = app

    def collect(self) -> AppSummary:
        module_summaries = {module.name: self._calc_module_summary(module) for module in self.app.modules.all()}
        return AppSummary(app_code=self.app.code, app_type=self.app.type, modules=module_summaries)

    def _calc_module_summary(self, module: Module) -> ModuleSummary:
        stag_env = module.get_envs(AppEnvName.STAG)
        prod_env = module.get_envs(AppEnvName.PROD)
        return ModuleSummary(envs={env.environment: self._calc_env_summaries(env) for env in [stag_env, prod_env]})

    def _calc_env_summaries(self, env: ModuleEnvironment) -> EnvSummary:
        latest_deployment = Deployment.objects.filter(app_environment=env).order_by("-created").first()
        return EnvSummary(
            latest_deployer=get_username_by_bkpaas_user_id(latest_deployment.operator) if latest_deployment else None,
            latest_deployed_at=latest_deployment.created if latest_deployment else None,
        )
