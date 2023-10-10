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
from typing import List, Optional

from paasng.platform.applications.models import Application

from .app_rule import AppScopedRuleConfig, ModuleScopedRuleConfig, RuleConfig, get_supported_alert_codes
from .constants import DEFAULT_RULE_CONFIGS, RUN_ENVS


class AppRuleConfigGenerator:
    """告警规则配置生成器"""

    def __init__(self, application: Application, default_receivers: List[str]):
        self.application = application
        self.app_code = application.code
        self.default_receivers = default_receivers
        self.supported_alerts = get_supported_alert_codes(application.type)

    def gen_app_scoped_rule_configs(
        self, run_envs: Optional[List[str]] = None, alert_codes: Optional[List[str]] = None
    ) -> List[RuleConfig]:
        """generate app scoped alert rule configs"""
        rule_configs: List[RuleConfig] = []
        run_envs = run_envs or RUN_ENVS

        for alert_code in alert_codes or self.supported_alerts.app_scoped_codes:
            r_configs = [
                AppScopedRuleConfig(
                    alert_code=alert_code,
                    app_code=self.app_code,
                    run_env=env,
                    threshold_expr=DEFAULT_RULE_CONFIGS[alert_code]['threshold_expr'],
                    receivers=self.default_receivers,
                )
                for env in run_envs
            ]
            rule_configs.extend([c for c in r_configs if c.is_valid()])

        return rule_configs

    def gen_module_scoped_rule_configs(
        self, module_name: str, run_envs: Optional[List[str]] = None, alert_codes: Optional[List[str]] = None
    ) -> List[RuleConfig]:
        """generate app module scoped alert rule configs by module_name"""
        rule_configs: List[RuleConfig] = []
        run_envs = run_envs or RUN_ENVS

        for alert_code in alert_codes or self.supported_alerts.module_scoped_codes:
            r_configs = [
                ModuleScopedRuleConfig(
                    alert_code=alert_code,
                    app_code=self.app_code,
                    run_env=env,
                    module_name=module_name,
                    threshold_expr=DEFAULT_RULE_CONFIGS[alert_code]['threshold_expr'],
                    receivers=self.default_receivers,
                )
                for env in run_envs
            ]
            rule_configs.extend([c for c in r_configs if c.is_valid()])

        return rule_configs
