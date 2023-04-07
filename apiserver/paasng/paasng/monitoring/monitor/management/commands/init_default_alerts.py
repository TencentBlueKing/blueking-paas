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
import time
from typing import List, Optional

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from paasng.monitoring.monitor.alert_rules.ascode import exceptions
from paasng.monitoring.monitor.alert_rules.manager import AlertRuleManager
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = 'Init default alert rules for applications'

    def add_arguments(self, parser):
        parser.add_argument('--apps', nargs='*', help='specified app code list. optional, default: all')

    def handle(self, *args, **options):
        app_qs = self._get_app_qs(options.get('apps'))

        for app in app_qs:
            # sleep 1s, 减小对监控接口的压力
            time.sleep(1)
            self._init_rules(app)

    def _get_app_qs(self, apps: Optional[List[str]]) -> QuerySet:
        if not apps:
            return Application.objects.filter(is_active=True, is_deleted=False)

        app_qs = Application.objects.filter(code__in=apps, is_active=True, is_deleted=False)

        if app_qs.count() != len(apps):
            valid_apps = app_qs.values_list('code', flat=True)
            invalid_apps = set(apps) - set(valid_apps)
            self.stdout.write(self.style.WARNING(f"apps({', '.join(invalid_apps)}) does not exist or is offline"))

        return app_qs

    def _init_rules(self, app: Application):
        try:
            AlertRuleManager(app).init_rules()
        except exceptions.AsCodeAPIError as e:
            self.stdout.write(self.style.ERROR(f'Init default alert rules for {app.code} failed: {e}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Init default alert rules for {app.code} success'))
