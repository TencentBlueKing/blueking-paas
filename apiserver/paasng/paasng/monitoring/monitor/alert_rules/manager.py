# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import Dict, List

from paasng.monitoring.monitor.models import AppAlertRule
from paasng.platform.applications.models import Application

from .ascode.client import AsCodeClient
from .config import AppRuleConfigGenerator, RuleConfig


class AlertRuleManager:
    """告警规则管理器"""

    def __init__(self, application: Application):
        self.application = application
        self.app_code = self.application.code
        self.default_receivers = application.get_developers()
        self.config_generator = AppRuleConfigGenerator(self.application, self.default_receivers)

    def init_rules(self):
        """为 app 初始化告警规则. 其中规则包括了 app scoped 和 app module scoped

        使用场景:
        - app 首次创建时, 初始化告警规则
        - app 迁移告警规则(从 bcs 迁移至 bkmonitor)
        """
        # init app scoped alert rule configs
        rule_configs = self.config_generator.gen_initial_app_rule_configs()

        # extend app module scoped alert rule configs
        module_names = self.application.modules.values_list('name', flat=True)
        for module_name in module_names:
            rule_configs.extend(self.config_generator.gen_initial_module_rule_configs(module_name))

        self._apply_rule_configs(rule_configs)
        self._save_rule_configs(rule_configs)

    def create_module_rules(self, module_name: str):
        """为新 module 创建告警规则

        :param module_name: 新模块名
        """
        module_rule_configs = self.config_generator.gen_initial_module_rule_configs(module_name)

        rule_configs = self.config_generator.gen_rule_configs_from_qs(
            AppAlertRule.objects.filter(application=self.application)
        )
        rule_configs.extend(module_rule_configs)

        self._apply_rule_configs(rule_configs)
        self._save_rule_configs(module_rule_configs)

    def update_rule(self, rule_obj: AppAlertRule, update_fields: Dict) -> AppAlertRule:
        """更新 app 的告警规则

        :param rule_obj: 待更新的告警规则
        :param update_fields: 更新的字段值. 目前仅支持更新 enabled, threshold_expr 和 receivers
        """
        rule_configs = self.config_generator.gen_rule_configs_from_qs(AppAlertRule.objects.exclude(id=rule_obj.id))
        new_rule_config = self.config_generator.gen_rule_config_from_obj(rule_obj, update_fields)

        self._apply_rule_configs(rule_configs + [new_rule_config])

        rule_obj.__dict__.update(update_fields)
        rule_obj.save()

        return rule_obj

    def refresh_rules(self):
        """向 bkmonitor 刷新 app 的告警规则(从已存在的 AppAlertRule queryset 读取后刷新)

        使用场景:
        - app 删除 module 后, 刷新告警规则
        """
        existed_rule_configs = self.config_generator.gen_rule_configs_from_qs(
            AppAlertRule.objects.filter(application=self.application)
        )
        self._apply_rule_configs(existed_rule_configs)

    def _apply_rule_configs(self, rule_configs: List[RuleConfig]):
        """通过 MonitorAsCode 方式下发告警规则到 bkmonitor"""
        client = AsCodeClient(self.app_code, rule_configs=rule_configs, default_receivers=self.default_receivers)
        client.apply_rule_configs()

    def _save_rule_configs(self, rule_configs: List[RuleConfig]):
        """配置录入 AppAlertRule Model"""
        rules: List[AppAlertRule] = [config.to_alert_rule_obj() for config in rule_configs]
        AppAlertRule.objects.bulk_create(rules)
