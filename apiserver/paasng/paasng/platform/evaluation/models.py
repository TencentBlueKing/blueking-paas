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
from django.db import models

from paasng.platform.applications.models import Application
from paasng.platform.evaluation.constants import OperationIssueType


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
    # 运维操作
    last_deployed_at = models.DateTimeField(verbose_name="最新部署时间", null=True)
    operator = models.CharField(verbose_name="最新部署人", max_length=128, null=True)
    # 汇总
    issue_type = models.CharField(verbose_name="问题类型", default=OperationIssueType.NONE, max_length=32)
    issues = models.JSONField(verbose_name="问题详情", default=list)
    collected_at = models.DateTimeField(verbose_name="采集时间")
