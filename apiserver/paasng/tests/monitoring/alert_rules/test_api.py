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

from paasng.monitoring.monitor.alert_rules.constants import DEFAULT_RULE_CONFIGS
from paasng.monitoring.monitor.alert_rules.manager import AlertRuleManager
from paasng.monitoring.monitor.models import AppAlertRule

pytestmark = pytest.mark.django_db


class TestAlertRulesView:
    @pytest.fixture(autouse=True)
    def init_rules(self, bk_app):
        manager = AlertRuleManager(bk_app)
        manager.init_rules()

    def test_list_rules(self, api_client, bk_app, bk_module):
        resp = api_client.get(
            f'/api/monitor/applications/{bk_app.code}/modules/{bk_module.name}/alert_rules/?keyword=CPU'
        )
        assert len(resp.data) == 2

        resp = api_client.get(
            f'/api/monitor/applications/{bk_app.code}/modules/{bk_module.name}/alert_rules/?alert_code=ddd'
        )
        assert len(resp.data) == 0

    def test_update_rule(self, api_client, bk_app):
        threshold_expr = '> 10 < 50'
        rule_obj = AppAlertRule.objects.all()[0]
        resp = api_client.put(
            f'/api/monitor/applications/{bk_app.code}/alert_rules/{rule_obj.id}/',
            {'threshold_expr': threshold_expr, 'receivers': rule_obj.receivers, 'enabled': rule_obj.enabled},
        )
        assert resp.status_code == 200
        assert AppAlertRule.objects.get(id=rule_obj.id).threshold_expr == threshold_expr

    def test_list_supported_alerts(self, api_client):
        resp = api_client.get('/api/monitor/supported_alerts/')
        alert_info = {alert['alert_code']: alert['display_name'] for alert in resp.data}
        assert alert_info['high_cpu_usage'] == DEFAULT_RULE_CONFIGS['module_scoped']['high_cpu_usage']['display_name']
