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
import importlib

import pytest
from django.test.utils import override_settings

from paasng.misc.monitoring.monitor.alert_rules import manager as alert_rules_manager
from paasng.misc.monitoring.monitor.alert_rules.config.constants import DEFAULT_RULE_CONFIGS

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAlertRulesView:
    @pytest.fixture(autouse=True)
    def _init_rules(self, bk_app, wl_namespaces):
        with override_settings(ENABLE_BK_MONITOR=True):
            importlib.reload(alert_rules_manager)
            manager = alert_rules_manager.alert_rule_manager_cls(bk_app)
        manager.init_rules()

    def test_list_rules(self, api_client, bk_app, bk_module):
        resp = api_client.get(
            f"/api/monitor/applications/{bk_app.code}/modules/{bk_module.name}/alert_rules/?keyword=CPU"
        )
        assert len(resp.data) == 2

        resp = api_client.get(
            f"/api/monitor/applications/{bk_app.code}/modules/{bk_module.name}/alert_rules/?alert_code=ddd"
        )
        assert len(resp.data) == 0

    def test_list_supported_alert_rules(self, api_client):
        resp = api_client.get("/api/monitor/supported_alert_rules/")
        alert_info = {alert["alert_code"]: alert["display_name"] for alert in resp.data}
        assert alert_info["high_cpu_usage"] == DEFAULT_RULE_CONFIGS["high_cpu_usage"]["display_name"]


class TestInitAlertRulesAPI:
    def test_init_alert_rules(self, api_client, bk_app, wl_namespaces):
        resp = api_client.post(f"/api/monitor/applications/{bk_app.code}/alert_rules/init/")
        assert resp.status_code == 200
