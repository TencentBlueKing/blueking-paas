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
from typing import List

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from paasng.misc.monitoring.monitor.dashboards.manager import bk_dashboard_manager_cls
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--app_codes", nargs="*", default=[], help="specified app code list. optional, default: all"
        )

    def handle(self, app_codes, *args, **options):
        """按应用 ID 导入仪表盘，可用于：

        - 功能上线后，批量初始化存量应用仪表盘
        """
        app_qs = Application.objects.filter(is_active=True, is_deleted=False)
        if app_codes:
            app_qs = app_qs.filter(code__in=app_codes)
            # 通过 --apps 指定应用时, 需要记录无效的 app_code
            if len(app_qs) != len(app_codes):
                self._write_invalid_codes(app_codes, app_qs)

        for app in app_qs:
            # sleep 1s, 减小对监控接口的压力
            self.stdout.write("Waiting for one second before sending the request to initialize dashboards ...")
            time.sleep(1)
            self._init_dashboards(app)

    def _write_invalid_codes(self, app_codes: List[str], app_qs: QuerySet):
        invalid_app_codes = set(app_codes) - set(app_qs.values_list("code", flat=True))
        for code in invalid_app_codes:
            self.stdout.write(self.style.ERROR(f"Initialize dashboard for {code} failed: app is invalid or offline"))

    def _init_dashboards(self, app: Application):
        try:
            bk_dashboard_manager_cls(app).init_builtin_dashboard()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Initialize dashboards for {app.code} failed: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Initialize dashboards for {app.code} success"))
