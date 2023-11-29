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

from paasng.misc.monitoring.monitor.alert_rules.config.constants import DEFAULT_RULE_CONFIGS
from paasng.misc.monitoring.monitor.alert_rules.manager import AlertRuleManager, get_supported_alert_codes
from paasng.misc.monitoring.monitor.models import AppAlertRule

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAlertRuleManager:
    def test_init_rules(
        self,
        bk_app,
        mock_import_configs,
        bk_app_init_rule_configs,
    ):
        manager = AlertRuleManager(bk_app)
        manager.init_rules()

        assert mock_import_configs.call_count == 2
        rule_configs, notice_group_config = bk_app_init_rule_configs
        expected_args = [
            ((notice_group_config, f"{bk_app.code}_notice_group"), {"incremental": False}),
            ((rule_configs,),),
        ]
        assert mock_import_configs.call_args_list == expected_args

        assert AppAlertRule.objects.filter(application=bk_app, alert_code="high_cpu_usage").count() == 2

    def test_create_rules(self, bk_app, wl_namespaces):
        manager = AlertRuleManager(bk_app)
        manager.create_rules(bk_app.get_default_module().name, "stag")
        assert AppAlertRule.objects.filter_app_scoped(bk_app).count() == len(
            get_supported_alert_codes(bk_app.type).app_scoped_codes
        )
        assert AppAlertRule.objects.filter_module_scoped(bk_app).count() == len(
            get_supported_alert_codes(bk_app.type).module_scoped_codes
        )
        assert (
            AppAlertRule.objects.get(application=bk_app, alert_code="high_cpu_usage").threshold_expr
            == DEFAULT_RULE_CONFIGS["high_cpu_usage"]["threshold_expr"]
        )

    def test_update_notice_group(self, bk_app, mock_import_configs):
        manager = AlertRuleManager(bk_app)
        manager.update_notice_group()

        mock_import_configs.assert_called()
