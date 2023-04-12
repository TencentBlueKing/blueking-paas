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

import cattr
from attrs import define, field
from django.db.models import QuerySet
from typing_extensions import Protocol

from paasng.monitoring.monitor.models import AppAlertRule
from paasng.platform.applications.models import Application

from .constants import DEFAULT_RULE_CONFIGS, RUN_ENVS


class RuleConfig(Protocol):
    alert_code: str  # protocol instance variables
    app_code: str
    run_env: str
    enabled: bool
    threshold_expr: str
    receivers: List[str]
    alert_rule_name: str
    alert_rule_display_name: Optional[str]

    @classmethod
    def from_alert_rule_obj(cls, rule_obj: AppAlertRule, override_fields: Optional[Dict] = None) -> 'RuleConfig':
        ...

    def to_alert_rule_obj(self) -> AppAlertRule:
        ...

    def to_dict(self) -> Dict:
        ...


@define(kw_only=True)
class AppRuleConfig:
    """app 维度告警策略配置

    :param alert_code: 告警策略标识
    :param app_code: 应用 code
    :param run_env: 运行环境(stag|prod)
    :param enabled: 规则是否启用. 默认启用(True)
    :param threshold_expr: 告警阈值表达式
    :param receivers: 告警接收者
    :param alert_rule_name: 告警策略英文全名
    :param alert_rule_display_name: 告警策略展示名称
    """

    alert_code: str
    app_code: str
    run_env: str
    enabled: bool = True
    threshold_expr: str
    receivers: List[str]
    alert_rule_name: str = field(init=False)
    alert_rule_display_name: Optional[str] = None

    def __attrs_post_init__(self):
        self.alert_rule_name = f'{self.app_code}_{self.run_env}_{self.alert_code}'

        default_configs = DEFAULT_RULE_CONFIGS['app_scoped'][self.alert_code]
        if not self.alert_rule_display_name:
            self.alert_rule_display_name = f"[{self.app_code}:{self.run_env}] {default_configs['display_name']}"

    @classmethod
    def from_alert_rule_obj(cls, rule_obj: AppAlertRule, override_fields: Optional[Dict] = None) -> 'AppRuleConfig':
        override_fields = override_fields or {}
        return cls(
            alert_code=rule_obj.alert_code,
            app_code=rule_obj.application.code,
            run_env=rule_obj.environment,
            alert_rule_display_name=rule_obj.display_name,
            enabled=override_fields.get('enabled') or rule_obj.enabled,
            threshold_expr=override_fields.get('threshold_expr') or rule_obj.threshold_expr,
            receivers=override_fields.get('receivers') or rule_obj.receivers,
        )

    def to_alert_rule_obj(self) -> AppAlertRule:
        application = Application.objects.get(code=self.app_code)
        return AppAlertRule(
            alert_code=self.alert_code,
            display_name=self.alert_rule_display_name,
            enabled=self.enabled,
            threshold_expr=self.threshold_expr,
            receivers=self.receivers or application.get_developers(),
            application=application,
            environment=self.run_env,
            module=None,
        )

    def to_dict(self) -> Dict:
        return cattr.unstructure(self)


@define
class AppModuleRuleConfig(AppRuleConfig):
    """app 模块维度的告警策略配置, 如 default 模块的 cpu 使用率过高的告警

    :param module_name: 模块名
    :param namespace: 模块所处的集群命名空间
    """

    module_name: str
    namespace: Optional[str] = None

    def __attrs_post_init__(self):
        self.alert_rule_name = f'{self.app_code}_{self.module_name}_{self.run_env}_{self.alert_code}'

        default_configs = DEFAULT_RULE_CONFIGS['module_scoped'][self.alert_code]
        if not self.alert_rule_display_name:
            self.alert_rule_display_name = (
                f"[{self.app_code}:{self.module_name}:{self.run_env}] {default_configs['display_name']}"
            )

        if not self.namespace:
            self.namespace = (
                Application.objects.get(code=self.app_code).get_engine_app(self.run_env, self.module_name).name
            )

    @classmethod
    def from_alert_rule_obj(
        cls, rule_obj: AppAlertRule, override_fields: Optional[Dict] = None
    ) -> 'AppModuleRuleConfig':
        override_fields = override_fields or {}
        return cls(
            alert_code=rule_obj.alert_code,
            app_code=rule_obj.application.code,
            run_env=rule_obj.environment,
            alert_rule_display_name=rule_obj.display_name,
            enabled=override_fields.get('enabled') or rule_obj.enabled,
            threshold_expr=override_fields.get('threshold_expr') or rule_obj.threshold_expr,
            receivers=override_fields.get('receivers') or rule_obj.receivers,
            module_name=rule_obj.module.name,
        )

    def to_alert_rule_obj(self) -> AppAlertRule:
        rule_obj = super().to_alert_rule_obj()
        rule_obj.module = rule_obj.application.get_module(self.module_name)
        return rule_obj


class AppRuleConfigGenerator:
    """告警规则配置生成器"""

    def __init__(self, application: Application, default_receivers: List[str]):
        self.application = application
        self.app_code = application.code
        self.default_receivers = default_receivers

    def gen_initial_app_rule_configs(self) -> List[RuleConfig]:
        """generate initial app scoped alert rule configs"""
        rule_configs: List[RuleConfig] = []

        if not DEFAULT_RULE_CONFIGS.get('app_scoped'):
            return rule_configs

        for alert_code, alert_config in DEFAULT_RULE_CONFIGS['app_scoped'].items():
            rule_configs.extend(
                [
                    AppRuleConfig(
                        alert_code=alert_code,
                        app_code=self.app_code,
                        run_env=env,
                        threshold_expr=alert_config['threshold_expr'],
                        receivers=self.default_receivers,
                    )
                    for env in RUN_ENVS
                ]
            )
        return rule_configs

    def gen_initial_module_rule_configs(self, module_name: str) -> List[RuleConfig]:
        """generate initial app module scoped alert rule configs by module_name"""
        rule_configs: List[RuleConfig] = []
        for alert_code, alert_config in DEFAULT_RULE_CONFIGS['module_scoped'].items():
            rule_configs.extend(
                [
                    AppModuleRuleConfig(
                        alert_code=alert_code,
                        app_code=self.app_code,
                        run_env=env,
                        module_name=module_name,
                        threshold_expr=alert_config['threshold_expr'],
                        receivers=self.default_receivers,
                    )
                    for env in RUN_ENVS
                ]
            )
        return rule_configs

    def gen_rule_configs_from_qs(self, qs: 'QuerySet[AppAlertRule]') -> List[RuleConfig]:
        """从 AppAlertRule queryset 中生成告警规则配置"""
        rule_configs: List[RuleConfig] = []
        config: RuleConfig

        for rule_obj in qs:
            if rule_obj.module:
                config = AppModuleRuleConfig.from_alert_rule_obj(rule_obj)
            else:
                config = AppRuleConfig.from_alert_rule_obj(rule_obj)

            rule_configs.append(config)

        return rule_configs

    def gen_rule_config_from_obj(self, rule_obj: AppAlertRule, override_fields: Optional[Dict] = None) -> RuleConfig:
        """从 AppAlertRule object 中生成告警规则配置

        :param rule_obj: 告警规则对象
        :param override_fields: 覆盖 rule_obj 中的字段
        """
        if rule_obj.module:
            return AppModuleRuleConfig.from_alert_rule_obj(rule_obj, override_fields)
        return AppRuleConfig.from_alert_rule_obj(rule_obj, override_fields)
