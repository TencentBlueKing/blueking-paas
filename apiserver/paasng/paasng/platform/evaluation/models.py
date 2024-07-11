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

from django.db import models

from paasng.platform.applications.models import Application
from paasng.platform.evaluation.constants import BatchTaskStatus, OperationIssueType
from paasng.utils.models import AuditedModel, BkUserField


class AppOperationReportCollectionTask(models.Model):
    """应用运营报告采集任务"""

    start_at = models.DateTimeField(verbose_name="任务开始时间", auto_now_add=True)
    end_at = models.DateTimeField(verbose_name="任务结束时间", null=True)
    total_count = models.IntegerField(verbose_name="应用总数", default=0)
    succeed_count = models.IntegerField(verbose_name="采集成功数", default=0)
    failed_count = models.IntegerField(verbose_name="采集失败数", default=0)
    failed_app_codes = models.JSONField(verbose_name="采集失败应用 Code 列表", default=list)
    status = models.CharField(
        verbose_name="任务状态",
        max_length=32,
        choices=BatchTaskStatus.get_choices(),
        default=BatchTaskStatus.RUNNING,
    )


class AppOperationReport(models.Model):
    """应用运营报告（含资源使用，用户活跃，运维操作等）"""

    app = models.OneToOneField(Application, on_delete=models.CASCADE, db_constraint=False)
    # 资源使用
    cpu_requests = models.IntegerField(verbose_name="CPU 请求", default=0)
    mem_requests = models.IntegerField(verbose_name="内存请求", default=0)
    cpu_limits = models.IntegerField(verbose_name="CPU 限制", default=0)
    mem_limits = models.IntegerField(verbose_name="内存限制", default=0)
    cpu_usage_avg = models.FloatField(verbose_name="CPU 平均使用率", default=0)
    mem_usage_avg = models.FloatField(verbose_name="内存平均使用率", default=0)
    res_summary = models.JSONField(verbose_name="资源使用详情汇总", default=dict)
    # 用户活跃度
    pv = models.BigIntegerField(verbose_name="近 30 天页面访问量", default=0)
    uv = models.BigIntegerField(verbose_name="近 30 天访问用户数", default=0)
    visit_summary = models.JSONField(verbose_name="用户访问详情汇总", default=dict)
    # 运维操作
    latest_deployed_at = models.DateTimeField(verbose_name="最新部署时间", null=True)
    latest_deployer = models.CharField(verbose_name="最新部署人", max_length=128, null=True)
    latest_operated_at = models.DateTimeField(verbose_name="最新操作时间", null=True)
    latest_operator = models.CharField(verbose_name="最新操作人", max_length=128, null=True)
    latest_operation = models.CharField(verbose_name="最新操作内容", max_length=128, null=True)
    deploy_summary = models.JSONField(verbose_name="部署详情汇总", default=dict)
    # 应用开发者 / 管理员
    administrators = models.JSONField(verbose_name="应用管理员", default=list)
    developers = models.JSONField(verbose_name="应用开发者", default=list)
    # 汇总
    issue_type = models.CharField(verbose_name="问题类型", default=OperationIssueType.NONE, max_length=32)
    evaluate_result = models.JSONField(verbose_name="评估结果", default=dict)
    collected_at = models.DateTimeField(verbose_name="采集时间")


class AppOperationEmailNotificationTask(models.Model):
    """应用运营报告邮件通知任务"""

    start_at = models.DateTimeField(verbose_name="任务开始时间", auto_now_add=True)
    end_at = models.DateTimeField(verbose_name="任务结束时间", null=True)
    total_count = models.IntegerField(verbose_name="应用总数", default=0)
    succeed_count = models.IntegerField(verbose_name="采集成功数", default=0)
    failed_count = models.IntegerField(verbose_name="采集失败数", default=0)
    failed_usernames = models.JSONField(verbose_name="通知失败的应用数量", default=list)
    notification_type = models.CharField(verbose_name="通知类型", max_length=64)
    status = models.CharField(
        verbose_name="任务状态",
        max_length=32,
        choices=BatchTaskStatus.get_choices(),
        default=BatchTaskStatus.RUNNING,
    )


class IdleAppNotificationMuteRule(AuditedModel):
    """闲置应用通知屏蔽规则"""

    user = BkUserField("屏蔽人")
    app_code = models.CharField("应用 Code", max_length=32)
    module_name = models.CharField("模块名称", max_length=32)
    environment = models.CharField("部署环境", max_length=32)
    expired_at = models.DateTimeField("过期时间")

    class Meta:
        unique_together = ("user", "app_code", "module_name", "environment")

    def __str__(self):
        return f"{self.user}-{self.app_code}-{self.module_name}-{self.environment}"
