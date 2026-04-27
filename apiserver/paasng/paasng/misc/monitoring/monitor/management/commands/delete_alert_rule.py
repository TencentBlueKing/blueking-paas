# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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


import time
from typing import TypedDict

from django.core.management.base import BaseCommand, CommandError

from paasng.infras.bkmonitorv3.client import make_bk_monitor_client
from paasng.infras.bkmonitorv3.params import QueryAlarmStrategiesParams
from paasng.misc.monitoring.monitor.models import AppAlertRule
from paasng.platform.applications.models import Application


class StrategyConfig(TypedDict):
    id: int
    version: str
    bk_biz_id: int
    name: str  # display name
    source: str
    scenario: str
    type: str
    items: list[dict]


class Command(BaseCommand):
    help = "Delete bkmonitor alert rule by alert_code"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--apps", nargs="+", help="app code list, eg: app1 app2")
        group.add_argument("--all-apps", action="store_true", help="run for all active applications")

        parser.add_argument("--alert-code", help="bkmonitor alert code")

    @staticmethod
    def get_applications(app_codes: list[str] | None) -> list[Application]:
        """获取待处理的应用列表"""
        app_qs = Application.objects.filter(is_active=True, is_deleted=False)
        if not app_codes:
            return list(app_qs)

        applications = app_qs.filter(code__in=app_codes)
        existing_app_codes = set(applications.values_list("code", flat=True))
        invalid_app_codes = set(app_codes) - existing_app_codes
        if invalid_app_codes:
            raise CommandError(f"Invalid app codes: {', '.join(sorted(invalid_app_codes))}")
        return list(applications)

    def print_available_alert_codes(self, applications: list[Application]):
        """打印指定应用下已有的 alert code, 供用户参考选择"""
        alert_codes = sorted(
            set(AppAlertRule.objects.filter(application__in=applications).values_list("alert_code", flat=True))
        )
        self.stdout.write("Available alert codes:\n\n")
        for code in alert_codes:
            self.stdout.write(code)
        self.stdout.write("\nSpecify an alert code using --alert-code")

    def handle(self, *args, **options):
        applications = self.get_applications(options.get("apps"))
        alert_code = options.get("alert_code")

        if not alert_code:
            self.print_available_alert_codes(applications)
            return

        self.stdout.write(self.style.WARNING("Deletion will begin in 3 seconds..."))
        time.sleep(3)

        for index, app in enumerate(applications):
            self.stdout.write(f"Processing app {index + 1}/{len(applications)}: {app.code}...")

            client = make_bk_monitor_client(app.tenant_id)

            try:
                alert_rules: list[StrategyConfig] = client.query_alarm_strategies(
                    QueryAlarmStrategiesParams(app_code=app.code, alert_code=alert_code)
                )["strategy_config_list"]
            except Exception as e:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f"Failed to query alert rules for app {app.code}. Error: {e}"))
                continue

            for alert_rule in alert_rules:
                resp = client.delete_alarm_strategy(strategy_config_id=alert_rule["id"], app_code=app.code)
                self.stdout.write(
                    f"Deleted alert rule '{alert_rule['name']}' (id={alert_rule['id']}) for app {app.code}. Gateway response: {resp}"
                )

            # 该命令处于测试阶段，等确认 bkmonitor 的告警规则被成功删除后，再删除数据库中的记录，避免误删告警规则后无法恢复
            # AppAlertRule.objects.filter(application=app, alert_code=alert_code).delete()

        self.stdout.write("DONE")
