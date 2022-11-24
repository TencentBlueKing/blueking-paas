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

from paasng.monitoring.monitor.alert_rules.manager import AlertRuleManager
from paasng.monitoring.monitor.models import AppAlertRule

pytestmark = pytest.mark.django_db


class TestAlertRuleManager:
    def test_init_rules(self, bk_app, mock_import_configs, bk_app_init_rule_configs):
        manager = AlertRuleManager(bk_app)
        manager.init_rules()
        mock_import_configs.assert_called_with(bk_app_init_rule_configs)
        assert AppAlertRule.objects.filter(alert_code='high_cpu_usage').count() == 2

    def test_create_module_rules(self, bk_app, create_module):
        manager = AlertRuleManager(bk_app)
        manager.create_module_rules(create_module.name)
        assert AppAlertRule.objects.filter(module=create_module, alert_code='high_cpu_usage').count() == 2

    def test_update(self, bk_app, cpu_usage_alert_rule_obj):
        from tests.utils.helpers import generate_random_string

        receivers = [generate_random_string(6)]
        manager = AlertRuleManager(bk_app)
        manager.update_rule(cpu_usage_alert_rule_obj, {'enabled': False, 'receivers': receivers})

        rule_obj = AppAlertRule.objects.get(id=cpu_usage_alert_rule_obj.id)
        assert rule_obj.enabled is False
        assert rule_obj.receivers == receivers
