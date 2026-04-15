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
from typing import List, Optional

from django.core.management.base import BaseCommand

from paasng.misc.monitoring.monitor.alert_rules.ascode import exceptions
from paasng.misc.monitoring.monitor.alert_rules.manager import alert_rule_manager_cls
from paasng.misc.monitoring.monitor.exceptions import BKMonitorNotSupportedError
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    """覆盖重建告警策略.

    当告警策略模板配置有误需要修正后重新下发时使用, 会以 overwrite=True 覆盖 bkmonitor 中已有的同名告警规则
    """

    help = "Recreate (overwrite) alert rules for applications"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="run for all active applications")
        group.add_argument("--apps", nargs="+", help="specified app code list")

        parser.add_argument(
            "--alert-codes",
            nargs="+",
            default=None,
            help="指定覆盖的告警策略(e.g. high_rabbitmq_queue_messages rabbitmq_instance_down), 不指定则重新初始化所有告警策略",
        )
        parser.add_argument(
            "--modules",
            nargs="+",
            default=None,
            help="指定模块名，不指定则所有模块",
        )

    def handle(self, *args, **options):
        app_codes: list[str] | None = options.get("apps")
        alert_codes: list[str] | None = options.get("alert_codes")
        module_names: list[str] | None = options.get("modules")

        app_qs = Application.objects.filter(is_active=True, is_deleted=False)
        if app_codes:
            app_qs = app_qs.filter(code__in=app_codes)
            invalid_app_codes = set(app_codes) - set(app_qs.values_list("code", flat=True))
            if invalid_app_codes:
                self.stdout.write(self.style.ERROR(f"Invalid app codes: {invalid_app_codes}, STOP recreate"))
                return

        for app in app_qs:
            # sleep 1s, 减小对监控接口的压力
            self.stdout.write(f"Recreating alert rules for app: {app.code} ...")
            time.sleep(1)
            self._recreate_rules(app, alert_codes=alert_codes, module_names=module_names)

    def _recreate_rules(
        self,
        app: Application,
        alert_codes: Optional[List[str]] = None,
        module_names: Optional[List[str]] = None,
    ):
        # 未指定模块时, 默认只对已部署过的模块执行覆盖重建
        if not module_names:
            module_names = list(app.modules.filter(last_deployed_date__isnull=False).values_list("name", flat=True))
            if not module_names:
                self.stdout.write(self.style.WARNING(f"No deployed modules found for {app.code}, skip"))
                return

        try:
            manager = alert_rule_manager_cls(app)
            manager.recreate_rules(alert_codes=alert_codes, module_names=module_names)
        except (exceptions.AsCodeAPIError, BKMonitorNotSupportedError) as e:
            self.stdout.write(self.style.ERROR(f"Recreate alert rules for {app.code} failed: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Recreate alert rules for {app.code} success"))
