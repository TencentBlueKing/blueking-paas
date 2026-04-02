# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable to the current version of the project
# delivered to anyone in the future.

import time

from django.core.management.base import BaseCommand

from paasng.misc.monitoring.monitor.alert_rules.ascode import exceptions
from paasng.misc.monitoring.monitor.alert_rules.manager import alert_rule_manager_cls
from paasng.misc.monitoring.monitor.exceptions import BKMonitorNotSupportedError
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = "Supplement alert rules for applications by app_code"

    def add_arguments(self, parser):
        parser.add_argument("--apps", nargs="+", required=True, help="specified app code list")

    def handle(self, *args, **options):
        app_codes = options["apps"]

        app_qs = Application.objects.filter(is_active=True, is_deleted=False, code__in=app_codes)
        invalid_app_codes = set(app_codes) - set(app_qs.values_list("code", flat=True))
        for code in invalid_app_codes:
            self.stdout.write(self.style.ERROR(f"Supplement alert rules for {code} failed: app is invalid or offline"))

        for app in app_qs:
            self.stdout.write(f"Supplementing alert rules for app: {app.code}")
            self._supplement_rules(app)

    def _supplement_rules(self, app: Application):
        try:
            manager = alert_rule_manager_cls(app)
        except BKMonitorNotSupportedError as e:
            self.stdout.write(self.style.ERROR(f"Supplement alert rules for {app.code} failed: {e}"))
            return

        module_names = app.modules.values_list("name", flat=True)
        run_envs = AppEnvironment.get_values()

        for module_name in module_names:
            for run_env in run_envs:
                time.sleep(1)
                try:
                    manager.create_rules(module_name, run_env)
                    self.stdout.write(
                        self.style.SUCCESS(f"Supplement alert rules for {app.code}/{module_name}/{run_env} success")
                    )
                except exceptions.AsCodeAPIError as e:
                    self.stdout.write(
                        self.style.ERROR(f"Supplement alert rules for {app.code}/{module_name}/{run_env} failed: {e}")
                    )
