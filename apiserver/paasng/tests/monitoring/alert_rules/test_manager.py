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
import pytest

from paasng.monitoring.monitor.alert_rules.config.constants import DEFAULT_RULE_CONFIGS
from paasng.monitoring.monitor.alert_rules.manager import AlertRuleManager, get_supported_alert_codes
from paasng.monitoring.monitor.models import AppAlertRule

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


class TestAlertRuleManager:
    def test_init_rules(
        self,
        bk_app,
        mock_import_configs,
        bk_app_init_rule_configs,
    ):
        manager = AlertRuleManager(bk_app)
        manager.init_rules()
        mock_import_configs.assert_called_with(bk_app_init_rule_configs)
        assert AppAlertRule.objects.filter(application=bk_app, alert_code='high_cpu_usage').count() == 2

    def test_refresh_rules_by_module(self, bk_app, wl_namespaces):
        manager = AlertRuleManager(bk_app)
        manager.refresh_rules_by_module(bk_app.get_default_module().name, 'stag')
        assert AppAlertRule.objects.filter(application=bk_app, module=None).count() == len(
            get_supported_alert_codes(bk_app.type).app_scoped_codes
        )
        assert AppAlertRule.objects.filter(application=bk_app).exclude(module=None).count() == len(
            get_supported_alert_codes(bk_app.type).module_scoped_codes
        )
        assert (
            AppAlertRule.objects.get(application=bk_app, alert_code='high_cpu_usage').threshold_expr
            == DEFAULT_RULE_CONFIGS['high_cpu_usage']['threshold_expr']
        )

    def test_refresh_rules_by_module_with_rule_obj(self, bk_app, wl_namespaces, cpu_usage_alert_rule_obj):
        manager = AlertRuleManager(bk_app)
        manager.refresh_rules_by_module(bk_app.get_default_module().name, 'stag')
        assert AppAlertRule.objects.filter(application=bk_app, module=None).count() == len(
            get_supported_alert_codes(bk_app.type).app_scoped_codes
        )
        assert AppAlertRule.objects.filter(application=bk_app).exclude(module=None).count() == len(
            get_supported_alert_codes(bk_app.type).module_scoped_codes
        )
        # 与 test_refresh_rules_by_module 不同, 这里测试 AlertRuleManager.refresh_rules_by_module 能够保留原 DB 中的配置值
        assert AppAlertRule.objects.get(id=cpu_usage_alert_rule_obj.id).threshold_expr == 'N/A'

    def test_update_rule(self, bk_app, wl_namespaces, cpu_usage_alert_rule_obj):
        from tests.utils.helpers import generate_random_string

        receivers = [generate_random_string(6)]
        manager = AlertRuleManager(bk_app)
        manager.update_rule(cpu_usage_alert_rule_obj, {'enabled': False, 'receivers': receivers})

        rule_obj = AppAlertRule.objects.get(id=cpu_usage_alert_rule_obj.id)
        assert rule_obj.enabled is False
        assert rule_obj.receivers == receivers

    def test_delete_rules(self, bk_app, cpu_usage_alert_rule_obj):
        module_name = bk_app.get_default_module().name
        assert AppAlertRule.objects.filter(application=bk_app, module__name=module_name).exists() is True
        manager = AlertRuleManager(bk_app)
        manager.delete_rules(module_name, 'stag')
        assert AppAlertRule.objects.filter(application=bk_app, module__name=module_name).exists() is False
