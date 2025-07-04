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

import logging
from dataclasses import asdict
from typing import List

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from paasng.infras.iam.helpers import fetch_role_members
from paasng.infras.iam.permissions.resources.application import ApplicationPermission
from paasng.misc.audit.models import AppOperationRecord
from paasng.platform.applications.constants import ApplicationRole, ApplicationType
from paasng.platform.applications.models import Application, JustLeaveAppManager
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models import Deployment
from paasng.platform.evaluation.collectors import AppDeploymentCollector, AppResQuotaCollector, AppUserVisitCollector
from paasng.platform.evaluation.constants import (
    BatchTaskStatus,
    EmailNotificationType,
    EmailReceiverType,
    OperationIssueType,
)
from paasng.platform.evaluation.evaluators import AppOperationEvaluator
from paasng.platform.evaluation.models import (
    AppOperationEmailNotificationTask,
    AppOperationReport,
    AppOperationReportCollectionTask,
)
from paasng.platform.evaluation.notifiers import AppOperationReportNotifier
from paasng.utils.basic import get_username_by_bkpaas_user_id

logger = logging.getLogger(__name__)


def _update_or_create_operation_report(app: Application):
    res_summary = AppResQuotaCollector(app).collect()
    # 统计资源配额 & 实际使用情况
    cpu_requests, mem_requests, cpu_limits, mem_limits = 0, 0, 0, 0
    cpu_usage_avg_val, mem_usage_avg_val = 0.0, 0.0
    for module in res_summary.modules.values():
        for procs in [
            module.envs[AppEnvName.STAG].procs,
            module.envs[AppEnvName.PROD].procs,
        ]:
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
    visit_summary = AppUserVisitCollector(app).collect()
    for mod in visit_summary.modules.values():
        for env in [mod.envs[AppEnvName.STAG], mod.envs[AppEnvName.PROD]]:
            total_pv += env.pv
            total_uv += env.uv

    # 统计部署情况
    deploy_summary = AppDeploymentCollector(app).collect()

    # 最近部署记录
    latest_deployment = Deployment.objects.filter(app_environment__application=app).order_by("-created").first()
    # 最新的操作记录
    latest_operation = AppOperationRecord.objects.filter(app_code=app.code).order_by("-created").first()

    defaults = {
        # 资源使用
        "cpu_requests": cpu_requests,
        "mem_requests": mem_requests,
        "cpu_limits": cpu_limits,
        "mem_limits": mem_limits,
        "cpu_usage_avg": round(cpu_usage_avg_val / cpu_limits, 4) if cpu_limits else 0,
        "mem_usage_avg": round(mem_usage_avg_val / mem_limits, 4) if mem_limits else 0,
        "res_summary": asdict(res_summary),
        # 用户活跃度
        "pv": total_pv,
        "uv": total_uv,
        "visit_summary": asdict(visit_summary),
        # 部署情况
        "latest_deployed_at": latest_deployment.created if latest_deployment else None,
        "latest_deployer": get_username_by_bkpaas_user_id(latest_deployment.operator) if latest_deployment else None,
        "latest_operated_at": latest_operation.created if latest_operation else None,
        "latest_operator": latest_operation.username if latest_operation else None,
        "latest_operation": latest_operation.get_display_text() if latest_operation else None,
        "deploy_summary": asdict(deploy_summary),
        # 应用开发者 / 管理员
        "administrators": fetch_role_members(app.code, ApplicationRole.ADMINISTRATOR),
        "developers": fetch_role_members(app.code, ApplicationRole.DEVELOPER),
        "collected_at": timezone.now(),
    }
    report, _ = AppOperationReport.objects.update_or_create(app=app, defaults=defaults)

    # 根据采集结果对应用运营情况进行评估
    evaluate_result = AppOperationEvaluator(report, res_summary, visit_summary, deploy_summary).evaluate()
    report.issue_type = evaluate_result.issue_type
    report.evaluate_result = asdict(evaluate_result)
    report.save(update_fields=["issue_type", "evaluate_result"])


@shared_task
def collect_and_update_app_operation_reports(app_codes: List[str]):
    """采集并更新指定应用的资源使用情况报告"""
    applications = Application.objects.exclude(type=ApplicationType.ENGINELESS_APP)
    # 应用已经被删除的，还保留报告是没有意义的
    AppOperationReport.objects.exclude(app__in=applications).delete()

    if app_codes:
        applications = applications.filter(code__in=app_codes)

    total_cnt, succeed_cnt = applications.count(), 0
    failed_app_codes = []
    task = AppOperationReportCollectionTask.objects.create(total_count=total_cnt)

    for idx, app in enumerate(applications, start=1):
        try:
            _update_or_create_operation_report(app)
        except Exception:
            failed_app_codes.append(app.code)
            logger.exception("failed to collect app: %s operation report", app.code)

        succeed_cnt += 1
        # 完整采集完需要较长时间，因此每隔一段时间更新下进度
        if idx % 20 == 0:
            task.succeed_count = succeed_cnt
            task.failed_count = len(failed_app_codes)
            task.save(update_fields=["succeed_count", "failed_count"])

    task.succeed_count = succeed_cnt
    task.failed_count = len(failed_app_codes)
    task.failed_app_codes = failed_app_codes
    task.status = BatchTaskStatus.FINISHED
    task.end_at = timezone.now()
    task.save(update_fields=["succeed_count", "failed_count", "failed_app_codes", "status", "end_at"])

    # 根据配置判断是否发送报告邮件给到平台管理员
    if settings.ENABLE_SEND_OPERATION_REPORT_EMAIL_TO_PLAT_MANAGE:
        reports = AppOperationReport.objects.exclude(issue_type=OperationIssueType.NONE)
        AppOperationReportNotifier().send(reports, EmailReceiverType.PLAT_ADMIN, settings.BKPAAS_PLATFORM_MANAGERS)


@shared_task
def send_idle_email_to_app_developers(
    tenant_id: str, app_codes: List[str], only_specified_users: List[str], exclude_specified_users: List[str]
):
    """发送应用闲置模块邮件给应用管理员/开发者"""
    reports = AppOperationReport.objects.filter(issue_type=OperationIssueType.IDLE)
    if app_codes:
        reports = reports.filter(app__code__in=app_codes)

    if not reports.exists():
        logger.info("no idle app reports, skip current notification task")
        return

    waiting_notify_usernames = set()
    for r in reports:
        waiting_notify_usernames.update(r.administrators)
        waiting_notify_usernames.update(r.developers)

    # 如果特殊指定用户，只发送给指定的用户
    if only_specified_users:
        waiting_notify_usernames &= set(only_specified_users)

    # 如果特别排除指定用户，则不发送给这些用户
    if exclude_specified_users:
        waiting_notify_usernames -= set(exclude_specified_users)

    total_cnt, succeed_cnt = len(waiting_notify_usernames), 0
    failed_usernames = []

    task = AppOperationEmailNotificationTask.objects.create(
        total_count=total_cnt, notification_type=EmailNotificationType.IDLE_APP_MODULE_ENVS
    )
    for idx, username in enumerate(waiting_notify_usernames):
        filters = ApplicationPermission().gen_develop_app_filters(username, tenant_id)
        # 如果无法获取到用户有权限的应用，直接跳过
        if not filters:
            continue

        app_codes = Application.objects.filter(is_active=True).filter(filters).values_list("code", flat=True)

        # 从缓存拿刚刚退出的应用 code exclude 掉，避免出现退出用户组，权限中心权限未同步的情况
        if just_leave_app_codes := JustLeaveAppManager(username).list():
            app_codes = [c for c in app_codes if c not in just_leave_app_codes]

        user_idle_app_reports = reports.filter(app__code__in=app_codes)

        if not user_idle_app_reports.exists():
            total_cnt -= 1
            logger.info("no idle app reports, skip notification to %s", username)
            continue

        try:
            AppOperationReportNotifier().send(user_idle_app_reports, EmailReceiverType.APP_DEVELOPER, [username])
        except Exception:
            failed_usernames.append(username)
            logger.exception("failed to send idle module envs email to %s", username)

        succeed_cnt += 1
        # 通知完所有用户需要较长时间，因此每隔一段时间更新下进度
        if idx % 20 == 0:
            task.succeed_count = succeed_cnt
            task.failed_count = len(failed_usernames)
            task.save(update_fields=["succeed_count", "failed_count"])

    task.total_count = total_cnt
    task.succeed_count = succeed_cnt
    task.failed_count = len(failed_usernames)
    task.failed_usernames = failed_usernames
    task.status = BatchTaskStatus.FINISHED
    task.end_at = timezone.now()
    task.save(update_fields=["total_count", "succeed_count", "failed_count", "failed_usernames", "status", "end_at"])
