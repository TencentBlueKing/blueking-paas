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

from unittest import mock

import pytest
import yaml
from django.test.utils import override_settings

from paasng.misc.monitoring.monitor.alert_rules.ascode.client import AsCodeClient
from paasng.misc.monitoring.monitor.alert_rules.config.app_rule import ModuleScopedRuleConfig
from paasng.misc.monitoring.monitor.alert_rules.config.constants import DEFAULT_RULE_CONFIGS
from paasng.misc.monitoring.monitor.alert_rules.config.entities import AlertCode
from paasng.misc.monitoring.monitor.alert_rules.config.metric_label import get_redis_bk_module

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

REDIS_ALERT_CODES = [
    AlertCode.HIGH_REDIS_MEMORY_USAGE.value,
    AlertCode.HIGH_REDIS_CONNECTION_USAGE.value,
    AlertCode.REDIS_OOM_KILLED.value,
]


class TestGetRedisBkModule:
    @pytest.mark.parametrize(
        ("env_vars", "expected"),
        [
            ({"REDIS_HOST": "127.0.0.1"}, "default"),
            ({}, ""),
        ],
    )
    def test_by_binding(self, env_vars, expected):
        with mock.patch(
            "paasng.misc.monitoring.monitor.alert_rules.config.metric_label._get_service_env_vars",
            return_value=env_vars,
        ):
            assert get_redis_bk_module("foo", "stag", "default") == expected

    def test_module_name_required(self):
        with pytest.raises(ValueError, match="module_name is required"):
            get_redis_bk_module("foo", "stag")


class TestRenderRedisRules:
    @pytest.mark.parametrize("alert_code", REDIS_ALERT_CODES)
    def test_render(self, bk_app, alert_code):
        rule_config = ModuleScopedRuleConfig(
            alert_code=alert_code,
            app_code=bk_app.code,
            run_env="prod",
            module_name="default",
            threshold_expr=DEFAULT_RULE_CONFIGS[alert_code]["threshold_expr"],
            receivers=["admin"],
            metric_labels={"bk_module": "default"},
        )

        with override_settings(REDIS_MONITOR_CONF={"enabled": True, "metric_name_prefix": "bkmonitor:redis:"}):
            configs = AsCodeClient(bk_app.code)._render_rule_configs([rule_config])

        rule = yaml.safe_load(configs[f"rule/{bk_app.code}-default-prod-{alert_code}.yaml"])
        metric = rule["query"]["query_configs"][0]["metric"]
        assert "bkmonitor:redis:redis_instance_" in metric
        assert f'bk_app_code="{bk_app.code}", bk_module="default", bk_env="prod"' in metric
        assert rule["detect"]["algorithm"]["fatal"][0]["config"] == DEFAULT_RULE_CONFIGS[alert_code]["threshold_expr"]
