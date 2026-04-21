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
from argparse import RawTextHelpFormatter

from django.core.management.base import BaseCommand

from paasng.misc.monitoring.monitor.alert_rules.ascode import exceptions
from paasng.misc.monitoring.monitor.alert_rules.manager import alert_rule_manager_cls
from paasng.misc.monitoring.monitor.exceptions import BKMonitorNotSupportedError
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = "覆盖创建监控侧告警策略， 会覆盖掉原有的同名告警策略，在需要更新告警策略时使用"

    def add_arguments(self, parser):
        parser.formatter_class = RawTextHelpFormatter
        parser.epilog = (
            "Examples:\n"
            "python manage.py recreate_alert_rules --apps app1 app2\n"
            "python manage.py recreate_alert_rules --all"
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="run for all active applications")
        group.add_argument("--apps", nargs="+", help="specified app code list")

    def handle(self, *args, **options):
        app_codes: list[str] | None = options.get("apps")

        app_qs = Application.objects.filter(is_active=True, is_deleted=False)
        if app_codes:
            app_qs = app_qs.filter(code__in=app_codes)
            invalid_app_codes = set(app_codes) - set(app_qs.values_list("code", flat=True))
            # 如果有无效的 app_codes，报错并退出执行
            if invalid_app_codes:
                self.stdout.write(
                    self.style.ERROR(
                        f"Found invalid app codes: {', '.join(sorted(invalid_app_codes))}. Please check the app codes and try again."
                    )
                )
                return

        for app in app_qs:
            # sleep 1s, 减小对监控接口的压力
            self.stdout.write(f"Recreating alert rules for app: {app.code} ...")
            time.sleep(1)
            self._recreate_rules(app)

    def _recreate_rules(self, app: Application):
        try:
            alert_rule_manager_cls(app).init_rules(overwrite=True)
        except (exceptions.AsCodeAPIError, BKMonitorNotSupportedError) as e:
            self.stdout.write(self.style.ERROR(f"Recreate alert rules for {app.code} failed: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Recreate alert rules for {app.code} success"))
