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

"""Collect application history metrics, evaluate suitable resource quota plan

Examples:

    # 仅评估指定的应用（支持列表）
    python manage.py evaluate_app_res_quota --codes app-code-1 app-code-2

    # 评估全量应用（性能不会很好）
    python manage.py evaluate_app_res_quota --all

    # 指定采样间隔 / 时间范围（默认：15m, 7d）
    python mange.py evaluate_app_res_quota --all --step 15m --time_range 7d
"""
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from paas_wl.bk_app.monitoring.metrics.evaluator import AppResQuotaEvaluator
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = 'Collect and statistics application history metrics'

    def add_arguments(self, parser):
        parser.add_argument("--codes", dest="app_codes", default=[], nargs='*', help="应用 Code 列表")
        parser.add_argument("--all", dest="evaluate_all", default=False, action="store_true", help="评估全量应用")
        parser.add_argument("--step", dest="step", default="15m", help="采样间隔")
        parser.add_argument("--time-range", dest="time_range", default="7d", help="采样时间范围")

    def handle(self, app_codes, evaluate_all, step, time_range, *args, **options):
        if not (evaluate_all or app_codes):
            raise ValueError("please specify --codes or --all")

        applications = Application.objects.all()
        if app_codes:
            applications = applications.filter(code__in=app_codes)

        summaries = []
        for app in applications:
            try:
                print(f'start evaluate app: {app.code}.....')
                summary = AppResQuotaEvaluator(app, step, time_range).evaluate()
            except Exception as e:
                print(f'failed to evaluate app: {app.code}, error: {str(e)}')
            else:
                summaries.append(asdict(summary))

        filename = f"app-res-used-summary-{datetime.now().isoformat('T', 'seconds')}.json"
        Path(filename).write_text(json.dumps(summaries, indent=4))
