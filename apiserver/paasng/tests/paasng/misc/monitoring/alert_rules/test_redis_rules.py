# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from types import SimpleNamespace
from unittest import mock

import pytest
import yaml
from django.test.utils import override_settings

from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.misc.monitoring.monitor.alert_rules.ascode.client import AsCodeClient
from paasng.misc.monitoring.monitor.alert_rules.config.app_rule import ModuleScopedRuleConfig
from paasng.misc.monitoring.monitor.alert_rules.config.constants import DEFAULT_RULE_CONFIGS
from paasng.misc.monitoring.monitor.alert_rules.config.entities import AlertCode

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SERVICE_MGR_PATH = "paasng.misc.monitoring.monitor.alert_rules.config.metric_label.mixed_service_mgr"


def _rel_with_plan_config(config: dict):
    return SimpleNamespace(get_plan=lambda: SimpleNamespace(config=config))


class TestRedisRuleValidity:
    """只有绑定了开启 monitor 套餐的 Redis 实例的模块才下发规则"""

    @pytest.mark.parametrize(
        ("rels", "expected"),
        [
            ([], False),
            ([_rel_with_plan_config({})], False),
            ([_rel_with_plan_config({"monitor": False})], False),
            ([_rel_with_plan_config({"monitor": True})], True),
        ],
    )
    def test_by_binding(self, bk_app, rels, expected):
        with mock.patch(SERVICE_MGR_PATH) as mgr:
            mgr.list_provisioned_rels.return_value = rels
            rule_config = self._make_rule_config(bk_app)

        assert rule_config.is_valid() is expected

    def test_service_not_found(self, bk_app):
        with mock.patch(SERVICE_MGR_PATH) as mgr:
            mgr.find_by_name.side_effect = ServiceObjNotFound("not found")
            rule_config = self._make_rule_config(bk_app)

        assert rule_config.is_valid() is False

    @staticmethod
    def _make_rule_config(bk_app) -> ModuleScopedRuleConfig:
        alert_code = AlertCode.HIGH_REDIS_MEMORY_USAGE.value
        return ModuleScopedRuleConfig(
            alert_code=alert_code,
            app_code=bk_app.code,
            run_env="prod",
            module_name="default",
            threshold_expr=DEFAULT_RULE_CONFIGS[alert_code]["threshold_expr"],
            receivers=["admin"],
        )


class TestRenderRedisRules:
    @pytest.mark.parametrize(
        ("alert_code", "expr"),
        [
            (
                AlertCode.HIGH_REDIS_MEMORY_USAGE.value,
                "max by (bk_instance) (bkmonitor:redis:redis_instance_memory_usage_rate",
            ),
            (
                AlertCode.HIGH_REDIS_CONNECTION_USAGE.value,
                "max by (bk_instance) (bkmonitor:redis:redis_instance_connection_usage_rate",
            ),
            (AlertCode.REDIS_OOM_KILLED.value, "max by (bk_instance) (bkmonitor:redis:redis_instance_oom_killed"),
            (AlertCode.REDIS_UNAVAILABLE.value, "min by (bk_instance) (bkmonitor:redis:redis_instance_alive"),
        ],
    )
    def test_render(self, bk_app, alert_code, expr):
        rule_config = ModuleScopedRuleConfig(
            alert_code=alert_code,
            app_code=bk_app.code,
            run_env="prod",
            module_name="default",
            threshold_expr=DEFAULT_RULE_CONFIGS[alert_code]["threshold_expr"],
            receivers=["admin"],
            metric_labels={"redis_bk_module": "default"},
        )

        with override_settings(REDIS_MONITOR_CONF={"enabled": True, "metric_name_prefix": "bkmonitor:redis:"}):
            configs = AsCodeClient(bk_app.code)._render_rule_configs([rule_config])

        rule = yaml.safe_load(configs[f"rule/{bk_app.code}-default-prod-{alert_code}.yaml"])
        assert rule["query"]["query_configs"][0]["metric"] == (
            f'{expr}{{bk_app_code="{bk_app.code}", bk_module="default", bk_env="prod"}})'
        )
        assert rule["detect"]["algorithm"]["fatal"][0]["config"] == DEFAULT_RULE_CONFIGS[alert_code]["threshold_expr"]
