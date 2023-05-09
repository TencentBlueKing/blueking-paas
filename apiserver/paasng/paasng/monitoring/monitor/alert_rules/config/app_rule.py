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

import cattrs
from attrs import define, field
from typing_extensions import Protocol

from paasng.monitoring.monitor.models import AppAlertRule
from paasng.platform.applications.models import Application

from .constants import DEFAULT_RULE_CONFIGS
from .metric_label import get_metric_labels


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

    def is_valid(self) -> bool:
        """规则配置是否有效"""


@define(kw_only=True)
class AppScopedRuleConfig:
    """app 维度告警策略配置

    :param alert_code: 告警策略标识
    :param display_name: 告警策略展示名称
    :param app_code: 应用 code
    :param run_env: 运行环境(stag|prod)
    :param enabled: 规则是否启用. 默认启用(True)
    :param threshold_expr: 告警阈值表达式
    :param receivers: 告警接收者
    :param alert_rule_name: 告警策略英文全名
    :param alert_rule_display_name: 告警策略展示名称
    :param metric_labels: 监控指标的 metric labels
    """

    alert_code: str
    app_code: str
    run_env: str
    enabled: bool = True
    threshold_expr: str
    receivers: List[str]
    alert_rule_name: str = field(init=False)
    alert_rule_display_name: Optional[str] = None
    metric_labels: Dict[str, str] = field(factory=dict)

    def __attrs_post_init__(self):
        self.alert_rule_name = f'{self.app_code}-{self.run_env}-{self.alert_code}'

        display_name = DEFAULT_RULE_CONFIGS['app_scoped'][self.alert_code]['display_name']
        if not self.alert_rule_display_name:
            self.alert_rule_display_name = f"[{self.app_code}:{self.run_env}] {display_name}"

        if not self.metric_labels:
            self.metric_labels = {'app_code': self.app_code, 'run_env': self.run_env}

    @classmethod
    def from_alert_rule_obj(
        cls, rule_obj: AppAlertRule, override_fields: Optional[Dict] = None
    ) -> 'AppScopedRuleConfig':
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
        return cattrs.unstructure(self)

    def is_valid(self) -> bool:
        """规则配置是否有效"""
        if self.metric_labels:
            return True
        return False


@define
class ModuleScopedRuleConfig(AppScopedRuleConfig):
    """app 模块维度的告警策略配置, 如 default 模块的 cpu 使用率过高的告警

    :param module_name: 模块名
    """

    module_name: str

    def __attrs_post_init__(self):
        self.alert_rule_name = f'{self.app_code}-{self.module_name}-{self.run_env}-{self.alert_code}'

        r_configs = DEFAULT_RULE_CONFIGS['module_scoped'][self.alert_code]
        if not self.alert_rule_display_name:
            self.alert_rule_display_name = (
                f"[{self.app_code}:{self.module_name}:{self.run_env}] {r_configs['display_name']}"
            )

        if not self.metric_labels:
            self.metric_labels = get_metric_labels(
                r_configs['metric_label_names'], self.app_code, self.run_env, self.module_name
            )

    @classmethod
    def from_alert_rule_obj(
        cls, rule_obj: AppAlertRule, override_fields: Optional[Dict] = None
    ) -> 'ModuleScopedRuleConfig':
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
