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

"""Collect application resource usage report

Examples:

    # 仅采集指定的应用（支持列表）
    python manage.py collect_app_operation_report --codes app-code-1 app-code-2

    # 采集全量应用（性能不会很好）
    python manage.py collect_app_operation_report --all

    # 采集全量应用 + 异步执行
    python manage.py collect_app_operation_report --all --async
"""
from django.core.management.base import BaseCommand

from paasng.platform.evaluation.tasks import collect_and_update_app_operation_reports


class Command(BaseCommand):
    help = "Collect and statistics application history metrics"

    def add_arguments(self, parser):
        parser.add_argument("--codes", dest="app_codes", default=[], nargs="*", help="应用 Code 列表")
        parser.add_argument("--all", dest="collect_all", default=False, action="store_true", help="采集全量应用")
        parser.add_argument("--async", dest="async_run", default=False, action="store_true", help="异步执行")

    def handle(self, app_codes, collect_all, async_run, *args, **options):
        if not (collect_all or app_codes):
            raise ValueError("please specify --codes or --all")

        if async_run:
            collect_and_update_app_operation_reports.delay(app_codes)
        else:
            collect_and_update_app_operation_reports(app_codes)
