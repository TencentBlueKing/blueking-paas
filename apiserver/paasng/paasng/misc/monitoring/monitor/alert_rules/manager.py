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
from typing import List, Protocol, Type

from django.conf import settings

from paasng.misc.monitoring.monitor.models import AppAlertRule
from paasng.platform.applications.models import Application

from .ascode.client import AsCodeClient
from .config import AppRuleConfigGenerator, RuleConfig, get_supported_alert_codes

logger = logging.getLogger(__name__)


class ManagerProtocol(Protocol):
    def __init__(self, application: Application):
        ...

    def init_rules(self):
        ...

    def create_rules(self, module_name: str, run_env: str):
        ...

    def update_notice_group(self):
        ...


class AlertRuleManager:
    """告警规则管理器"""

    def __init__(self, application: Application):
        self.application = application
        self.app_code = self.application.code
        self.default_receivers = application.get_developers()
        self.config_generator = AppRuleConfigGenerator(self.application, self.default_receivers)
        self.supported_alerts = get_supported_alert_codes(application.type)
        self.client = AsCodeClient(self.app_code)

    def init_rules(self):
        """为 app 初始化告警规则. 其中规则包括了 app scoped 和 app module scoped

        使用场景:
        - app 首次创建时, 初始化告警规则
        - app 迁移告警规则(从 bcs 迁移至 bkmonitor)
        """
        # init app scoped alert rule configs
        rule_configs = self.config_generator.gen_app_scoped_rule_configs()

        # extend app module scoped alert rule configs
        module_names = self.application.modules.values_list("name", flat=True)
        for module_name in module_names:
            rule_configs.extend(self.config_generator.gen_module_scoped_rule_configs(module_name))

        if not rule_configs:
            return

        self._apply_rule_configs(rule_configs)
        self._save_rule_configs(rule_configs)

    def create_rules(self, module_name: str, run_env: str):
        """创建 app 的告警规则

        使用场景:
        - app 部署 module 后, 初始化告警规则
        """

        rule_configs = self._get_app_scoped_rules(run_env)
        rule_configs.extend(self._get_module_scoped_rules(module_name, run_env))

        if not rule_configs:
            return

        self._apply_rule_configs(rule_configs)
        self._save_rule_configs(rule_configs)

    def update_notice_group(self):
        """更新默认通知组"""
        self.client.apply_notice_group(self.default_receivers)

    def _get_app_scoped_rules(self, run_env: str) -> List[RuleConfig]:
        """获取待创建的 app scoped 告警规则"""
        rule_qs = AppAlertRule.objects.filter_app_scoped(self.application, run_env)
        existed_alert_codes = {r.alert_code for r in rule_qs}

        if new_alert_codes := set(self.supported_alerts.app_scoped_codes) - existed_alert_codes:
            return self.config_generator.gen_app_scoped_rule_configs([run_env], list(new_alert_codes))

        return []

    def _get_module_scoped_rules(self, module_name: str, run_env: str) -> List[RuleConfig]:
        """获取待创建的 module scoped 告警规则"""
        rule_qs = AppAlertRule.objects.filter_module_scoped(self.application, run_env, module_name)
        existed_alert_codes = {c.alert_code for c in rule_qs}

        if new_alert_codes := set(self.supported_alerts.module_scoped_codes) - existed_alert_codes:
            return self.config_generator.gen_module_scoped_rule_configs(module_name, [run_env], list(new_alert_codes))

        return []

    def _apply_rule_configs(self, rule_configs: List[RuleConfig]):
        """通过 MonitorAsCode 方式下发告警规则到 bkmonitor"""
        self.client.apply_notice_group(self.default_receivers)
        self.client.apply_rule_configs(rule_configs)

    def _save_rule_configs(self, rule_configs: List[RuleConfig]):
        """配置录入 AppAlertRule Model"""
        rules: List[AppAlertRule] = [config.to_alert_rule_obj() for config in rule_configs]
        for r in rules:
            AppAlertRule.objects.update_or_create(
                alert_code=r.alert_code,
                application=r.application,
                module=r.module,
                environment=r.environment,
                defaults={
                    "display_name": r.display_name,
                    "enabled": r.enabled,
                    "threshold_expr": r.threshold_expr,
                    "receivers": r.receivers,
                },
            )


class NullManager:
    def __init__(self, application: Application):
        ...

    def init_rules(self):
        ...

    def create_rules(self, module_name: str, run_env: str):
        ...

    def update_notice_group(self):
        ...


def get_alert_rule_manager_cls() -> Type[ManagerProtocol]:
    if not settings.ENABLE_BK_MONITOR:
        logger.warning("bkmonitor in this edition not enabled, skip apply Monitor Rules")
        return NullManager
    else:
        return AlertRuleManager


alert_rule_manager_cls = get_alert_rule_manager_cls()
