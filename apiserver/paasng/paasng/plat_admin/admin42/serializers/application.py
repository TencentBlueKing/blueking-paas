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
from typing import Any, Dict, List

import arrow
import pytz
from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.evaluation.constants import BatchTaskStatus
from paasng.platform.evaluation.models import AppOperationReport, AppOperationReportCollectionTask
from paasng.utils.datetime import humanize_timedelta
from paasng.utils.models import OrderByField

logger = logging.getLogger(__name__)


class ApplicationFilterSLZ(serializers.Serializer):
    """Serializer for application query filter"""

    valid_order_by_fields = ("code", "created", "latest_operated_at")

    is_active = serializers.BooleanField(required=False, allow_null=True, help_text="应用是否活跃")
    regions = serializers.ListField(required=False, help_text="应用 region")
    languages = serializers.ListField(required=False, help_text="应用开发语言")
    search_term = serializers.CharField(required=False, help_text="搜索关键字")
    source_origin = serializers.IntegerField(required=False, help_text="源码来源")
    market_enabled = serializers.BooleanField(
        required=False, default=None, allow_null=True, help_text="是否已开启市场"
    )
    order_by = serializers.ListField(default=["-created"], help_text="排序关键字")

    def validate_order_by(self, fields):
        for field in fields:
            f = OrderByField.from_string(field)
            if f.name not in self.valid_order_by_fields:
                raise ValidationError("无效的排序选项：%s" % f)
        return fields


class LegacyApplicationFilterSLZ(serializers.Serializer):
    only_include_legacy_v1_app = serializers.BooleanField(default=False, help_text="仅包括V1 PaaS应用")
    only_include_not_migrated_app = serializers.BooleanField(default=False, help_text="仅包括未迁移应用")
    include_downed_app = serializers.BooleanField(default=False, help_text="包括已下架应用")

    search_term = serializers.CharField(required=False, help_text="搜索关键字, 只搜索应用id")


class AppOperationReportListInputSLZ(serializers.Serializer):
    """应用运营评估报告列表查询参数"""

    search_term = serializers.CharField(required=False, help_text="搜索关键字")
    issue_type = serializers.CharField(required=False, help_text="问题类型")
    order_by = serializers.CharField(help_text="排序字段", default="-mem_limits")


class AppOperationReportCollectionTaskOutputSLZ(serializers.Serializer):
    """应用运营评估报告采集任务"""

    start_at = serializers.DateTimeField(help_text="任务开始时间")
    duration = serializers.SerializerMethodField(help_text="任务耗时")
    total_count = serializers.IntegerField(help_text="应用总数")
    succeed_count = serializers.IntegerField(help_text="采集成功数")
    failed_count = serializers.IntegerField(help_text="采集失败数")
    failed_app_codes = serializers.JSONField(help_text="采集失败应用 Code 列表")
    status = serializers.SerializerMethodField(help_text="任务状态")

    def get_duration(self, obj: AppOperationReportCollectionTask) -> str:
        if obj.end_at is None:
            return "--"

        return humanize_timedelta(obj.end_at - obj.start_at)

    def get_status(self, obj: AppOperationReportCollectionTask) -> str:
        return BatchTaskStatus.get_choice_label(obj.status)


class EnvDeploySummarySLZ(serializers.Serializer):
    latest_deployer = serializers.CharField(help_text="最新部署人", required=False)
    latest_deployed_at = serializers.SerializerMethodField(help_text="最新部署时间", required=False)

    def get_latest_deployed_at(self, obj: Dict[str, Any]) -> str:
        return (
            (
                arrow.get(obj["latest_deployed_at"])
                .astimezone(tz=pytz.timezone(settings.TIME_ZONE))
                .strftime("%Y-%m-%d %H:%M:%S")
            )
            if obj.get("latest_deployed_at")
            else "--"
        )


class ModuleDeploySummarySLZ(serializers.Serializer):
    envs = serializers.DictField(help_text="环境列表", child=EnvDeploySummarySLZ(), required=False)


class DeploySummarySLZ(serializers.Serializer):
    app_code = serializers.CharField(help_text="应用 Code", required=False)
    app_type = serializers.CharField(help_text="应用类型", required=False)
    modules = serializers.DictField(help_text="模块列表", child=ModuleDeploySummarySLZ(), required=False)


class AppOperationReportOutputSLZ(serializers.Serializer):
    """应用运营评估报告"""

    app_code = serializers.CharField(help_text="应用 Code", source="app.code")
    app_name = serializers.CharField(help_text="应用名称", source="app.name")
    mem_requests = serializers.SerializerMethodField(help_text="内存请求")
    mem_limits = serializers.SerializerMethodField(help_text="内存限制")
    mem_usage_avg = serializers.SerializerMethodField(help_text="内存平均使用率")
    cpu_requests = serializers.SerializerMethodField(help_text="CPU 请求")
    cpu_limits = serializers.SerializerMethodField(help_text="CPU 限制")
    cpu_usage_avg = serializers.SerializerMethodField(help_text="CPU 平均使用率")
    res_summary = serializers.JSONField(help_text="资源使用汇总")
    pv = serializers.IntegerField(help_text="PV")
    uv = serializers.IntegerField(help_text="UV")
    visit_summary = serializers.JSONField(help_text="访问汇总")
    latest_deployed_at = serializers.DateTimeField(help_text="最新部署时间")
    latest_deployer = serializers.CharField(help_text="最新部署人")
    latest_operated_at = serializers.DateTimeField(help_text="最新操作时间")
    latest_operator = serializers.CharField(help_text="最新操作人")
    latest_operation = serializers.CharField(help_text="最新操作内容")
    deploy_summary = DeploySummarySLZ(help_text="部署汇总")
    issue_type = serializers.CharField(help_text="问题类型")
    issues = serializers.SerializerMethodField(help_text="问题详情")
    evaluate_result = serializers.JSONField(help_text="评估结果")
    collected_at = serializers.DateTimeField(help_text="报告采集时间")

    def get_mem_requests(self, report: AppOperationReport) -> str:
        return f"{round(report.mem_requests / 1024, 2)} G"

    def get_mem_limits(self, report: AppOperationReport) -> str:
        return f"{round(report.mem_limits / 1024, 2)} G"

    def get_mem_usage_avg(self, report: AppOperationReport) -> str:
        return f"{round(report.mem_usage_avg * 100, 2)}%"

    def get_cpu_requests(self, report: AppOperationReport) -> str:
        return f"{round(report.cpu_requests / 1000, 2)} 核"

    def get_cpu_limits(self, report: AppOperationReport) -> str:
        return f"{round(report.cpu_limits / 1000, 2)} 核"

    def get_cpu_usage_avg(self, report: AppOperationReport) -> str:
        return f"{round(report.cpu_usage_avg * 100, 2)}%"

    def get_issues(self, report: AppOperationReport) -> List[str]:
        return report.evaluate_result["issues"] if report.evaluate_result else []
