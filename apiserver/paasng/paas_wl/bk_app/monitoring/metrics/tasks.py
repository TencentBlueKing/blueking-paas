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
import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import List

from celery import shared_task

from paas_wl.bk_app.monitoring.metrics.evaluator import AppResQuotaEvaluator
from paas_wl.bk_app.monitoring.metrics.models import AppResourceUsageReport
from paasng.accessories.paas_analysis.clients import SiteMetricsClient
from paasng.accessories.paas_analysis.constants import MetricSourceType
from paasng.accessories.paas_analysis.services import get_or_create_site_by_env
from paasng.platform.applications.models import Application
from paasng.platform.applications.operators import get_last_operator

logger = logging.getLogger(__name__)


def _update_or_create_usage_report(app: Application):
    summary = AppResQuotaEvaluator(app).evaluate()
    # 统计资源配额 & 实际使用情况
    cpu_requests, mem_requests, cpu_limits, mem_limits = 0, 0, 0, 0
    cpu_usage_avg_val, mem_usage_avg_val = 0.0, 0.0
    for mod in summary.modules:
        for procs in [mod.stag_procs, mod.prod_procs]:
            for proc in procs:
                # 没有副本数量的忽略
                if not proc.replicas:
                    continue

                if proc.quota:
                    cpu_requests += proc.replicas * proc.quota.requests.cpu
                    mem_requests += proc.replicas * proc.quota.requests.memory
                    cpu_limits += proc.replicas * proc.quota.limits.cpu
                    mem_limits += proc.replicas * proc.quota.limits.memory
                if proc.cpu:
                    cpu_usage_avg_val += proc.replicas * proc.cpu.avg
                if proc.memory:
                    mem_usage_avg_val += proc.replicas * proc.memory.avg

    # 统计近一周总访问量 & 用户数
    total_pv, total_uv = 0, 0
    end = date.today()
    start = end - timedelta(days=7)
    for module in app.modules.all():
        for env in module.envs.all():
            try:
                site = get_or_create_site_by_env(env)
                client = SiteMetricsClient(site, MetricSourceType.INGRESS)
                resp = client.get_total_page_view_metric_about_site(start, end)
            except Exception:
                logger.exception(
                    "failed to get app %s module %s env %s pv & uv", app.code, module.name, env.environment
                )
            else:
                total_pv += resp["result"]["results"]["pv"]
                total_uv += resp["result"]["results"]["uv"]

    AppResourceUsageReport.objects.update_or_create(
        app_code=app.code,
        defaults={
            "app_name": app.name,
            "cpu_requests": cpu_requests,
            "mem_requests": mem_requests,
            "cpu_limits": cpu_limits,
            "mem_limits": mem_limits,
            "cpu_usage_avg": round(cpu_usage_avg_val / cpu_limits, 4),
            "mem_usage_avg": round(mem_usage_avg_val / mem_limits, 4),
            "pv": total_pv,
            "uv": total_uv,
            "summary": asdict(summary),
            "operator": get_last_operator(app),
            "collected_at": datetime.now(),
        },
    )


@shared_task
def collect_and_update_app_res_usage_reports(app_codes: List[str]):
    """采集并更新指定应用的资源使用情况报告"""
    applications = Application.objects.all()
    if app_codes:
        applications = applications.filter(code__in=app_codes)

    total_cnt = applications.count()
    for idx, app in enumerate(applications, start=1):
        try:
            logger.info("[%d/%d] start collect app %s usage report.....", idx, total_cnt, app.code)
            _update_or_create_usage_report(app)
        except Exception:
            logger.exception("failed to collect app: %s usage report", app.code)
        else:
            logger.info("successfully collect app: %s usage report", app.code)
