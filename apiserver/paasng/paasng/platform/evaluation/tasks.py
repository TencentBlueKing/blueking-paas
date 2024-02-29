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
from datetime import date, timedelta
from typing import List

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from paasng.accessories.paas_analysis.clients import SiteMetricsClient
from paasng.accessories.paas_analysis.constants import MetricSourceType
from paasng.accessories.paas_analysis.services import get_or_create_site_by_env
from paasng.misc.operations.models import Operation
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.engine.models import Deployment
from paasng.platform.evaluation.collectors import AppResQuotaCollector
from paasng.platform.evaluation.constants import EmailReceiverType
from paasng.platform.evaluation.evaluators import AppOperationEvaluator
from paasng.platform.evaluation.models import AppOperationReport
from paasng.platform.evaluation.notifiers import AppOperationReportNotifier
from paasng.utils.basic import get_username_by_bkpaas_user_id

logger = logging.getLogger(__name__)


def _update_or_create_operation_report(app: Application):
    summary = AppResQuotaCollector(app).collect()
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

    # 统计近 30 天总访问量 & 用户数
    total_pv, total_uv = 0, 0
    end = date.today()
    start = end - timedelta(days=30)
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

    # 最近部署记录
    last_deployment = (
        Deployment.objects.filter(app_environment__application__code=app.code).order_by("-created").first()
    )
    # 最新的操作记录
    last_operation = Operation.objects.filter(application=app).order_by("-created").first()

    defaults = {
        "cpu_requests": cpu_requests,
        "mem_requests": mem_requests,
        "cpu_limits": cpu_limits,
        "mem_limits": mem_limits,
        "cpu_usage_avg": round(cpu_usage_avg_val / cpu_limits, 4) if cpu_limits else 0,
        "mem_usage_avg": round(mem_usage_avg_val / mem_limits, 4) if mem_limits else 0,
        "res_summary": asdict(summary),
        "pv": total_pv,
        "uv": total_uv,
        "last_deployed_at": last_deployment.created if last_deployment else None,
        "last_deployer": get_username_by_bkpaas_user_id(last_deployment.operator) if last_deployment else None,
        "last_operated_at": last_operation.created if last_operation else None,
        "last_operator": last_operation.get_operator() if last_operation else None,
        "last_operation": last_operation.get_operate_display() if last_operation else None,
        "collected_at": timezone.now(),
    }
    issue_type, issues = AppOperationEvaluator(app).evaluate(defaults)
    defaults.update({"issue_type": issue_type, "issues": issues})
    AppOperationReport.objects.update_or_create(app=app, defaults=defaults)


@shared_task
def collect_and_update_app_operation_reports(app_codes: List[str]):
    """采集并更新指定应用的资源使用情况报告"""
    applications = Application.objects.exclude(type=ApplicationType.ENGINELESS_APP)
    # 应用已经被删除的，还保留报告是没有意义的
    AppOperationReport.objects.exclude(app__in=applications).delete()

    if app_codes:
        applications = applications.filter(code__in=app_codes)

    total_cnt = applications.count()
    for idx, app in enumerate(applications, start=1):
        try:
            logger.info("[%d/%d] start collect app %s operation report.....", idx, total_cnt, app.code)
            _update_or_create_operation_report(app)
            logger.info("successfully collect app: %s operation report", app.code)
        except Exception:
            logger.exception("failed to collect app: %s operation report", app.code)

    # 根据配置判断是否发送报告邮件给到平台管理员
    if settings.ENABLE_SEND_OPERATION_REPORT_EMAIL_TO_PLAT_MANAGE:
        AppOperationReportNotifier().send(EmailReceiverType.PLAT_MANAGER, settings.BKPAAS_PLATFORM_MANAGERS)
