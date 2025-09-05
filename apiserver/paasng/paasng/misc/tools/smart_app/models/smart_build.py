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

from django.db import models

from paas_wl.utils.models import AuditedModel, UuidAuditedModel
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.engine.constants import JobStatus
from paasng.utils.models import BkUserField

logger = logging.getLogger(__name__)


class SmartBuildRecord(UuidAuditedModel):
    """s-mart 包构建记录"""

    source_origin = models.CharField(max_length=32, help_text="源码来源类型，如：源码包、代码仓库")
    package_name = models.CharField(max_length=128, blank=True, default="", help_text="源码包名称")
    app_code = models.CharField(max_length=64, help_text="应用的唯一标识")

    artifact_url = models.URLField(max_length=2048, blank=True, default="", help_text="s-mart 构建产物地址")
    status = models.CharField(max_length=12, default=JobStatus.PENDING.value, help_text="s-mart 构建任务运行状态")

    stream = models.OneToOneField(
        "SmartBuildLog", on_delete=models.CASCADE, null=True, related_name="smart_build", db_constraint=False
    )
    err_detail = models.TextField(blank=True, null=True, help_text="构建失败时的错误详情")

    start_time = models.DateTimeField(null=True, help_text="构建任务起始时间")
    end_time = models.DateTimeField(null=True, help_text="构建任务结束时间")
    operator = BkUserField()

    tenant_id = tenant_id_field_factory()

    def update_fields(self, **u_fields):
        logger.info("update_fields, smart_build_id: %s, fields: %s", self.uuid, u_fields)

        for key, value in u_fields.items():
            setattr(self, key, value)
        self.save()


class SmartBuildLog(UuidAuditedModel):
    tenant_id = tenant_id_field_factory()

    def write(self, line, stream="STDOUT"):
        if not line.endswith("\n"):
            line += "\n"
        SmartBuildLogLine.objects.create(smart_build_log=self, line=line, stream=stream)


class SmartBuildLogLine(AuditedModel):
    smart_build_log = models.ForeignKey(
        SmartBuildLog,
        related_name="lines",
        on_delete=models.CASCADE,
        db_constraint=False,
    )
    stream = models.CharField(max_length=16)
    line = models.TextField()

    tenant_id = tenant_id_field_factory()

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return "%s-%s" % (self.id, self.line)
