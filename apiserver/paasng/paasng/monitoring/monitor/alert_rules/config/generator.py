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
from typing import Dict, List, Optional

from django.db.models import QuerySet

from paasng.monitoring.monitor.models import AppAlertRule
from paasng.platform.applications.models import Application

from .app_rule import AppScopedRuleConfig, ModuleScopedRuleConfig, RuleConfig
from .constants import DEFAULT_RULE_CONFIGS, RUN_ENVS


class AppRuleConfigGenerator:
    """告警规则配置生成器"""

    def __init__(self, application: Application, default_receivers: List[str]):
        self.application = application
        self.app_code = application.code
        self.default_receivers = default_receivers

    def gen_app_scoped_rule_configs(self) -> List[RuleConfig]:
        """generate app scoped alert rule configs"""
        rule_configs: List[RuleConfig] = []

        if not DEFAULT_RULE_CONFIGS.get('app_scoped'):
            return rule_configs

        for alert_code, alert_config in DEFAULT_RULE_CONFIGS['app_scoped'].items():
            r_configs = [
                AppScopedRuleConfig(
                    alert_code=alert_code,
                    app_code=self.app_code,
                    run_env=env,
                    threshold_expr=alert_config['threshold_expr'],
                    receivers=self.default_receivers,
                )
                for env in RUN_ENVS
            ]
            rule_configs.extend([c for c in r_configs if c.is_valid()])

        return rule_configs

    def gen_module_scoped_rule_configs(self, module_name: str) -> List[RuleConfig]:
        """generate app module scoped alert rule configs by module_name"""
        rule_configs: List[RuleConfig] = []
        for alert_code, alert_config in DEFAULT_RULE_CONFIGS['module_scoped'].items():
            r_configs = [
                ModuleScopedRuleConfig(
                    alert_code=alert_code,
                    app_code=self.app_code,
                    run_env=env,
                    module_name=module_name,
                    threshold_expr=alert_config['threshold_expr'],
                    receivers=self.default_receivers,
                )
                for env in RUN_ENVS
            ]
            rule_configs.extend([c for c in r_configs if c.is_valid()])

        return rule_configs

    def gen_rule_configs_from_qs(self, qs: 'QuerySet[AppAlertRule]') -> List[RuleConfig]:
        """从 AppAlertRule queryset 中生成告警规则配置"""
        rule_configs: List[RuleConfig] = []
        config: RuleConfig

        for rule_obj in qs:
            if rule_obj.module:
                config = ModuleScopedRuleConfig.from_alert_rule_obj(rule_obj)
            else:
                config = AppScopedRuleConfig.from_alert_rule_obj(rule_obj)

            rule_configs.append(config)

        return rule_configs

    def gen_rule_config_from_obj(self, rule_obj: AppAlertRule, override_fields: Optional[Dict] = None) -> RuleConfig:
        """从 AppAlertRule object 中生成告警规则配置

        :param rule_obj: 告警规则对象
        :param override_fields: 覆盖 rule_obj 中的字段
        """
        if rule_obj.module:
            return ModuleScopedRuleConfig.from_alert_rule_obj(rule_obj, override_fields)
        return AppScopedRuleConfig.from_alert_rule_obj(rule_obj, override_fields)
