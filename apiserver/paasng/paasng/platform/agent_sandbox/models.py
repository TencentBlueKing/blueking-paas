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

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.applications.models import Application
from paasng.utils.models import BkUserField, UuidAuditedModel

from .constants import SandboxStatus


class Sandbox(UuidAuditedModel):
    """A sandbox is an isolated environment with filesystem and process management capabilities,
    typically used for running AI agent tasks.
    """

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="sandboxes")
    name = models.CharField(verbose_name="名称", max_length=64, help_text="租户内唯一，未提供时自动生成")

    snapshot = models.CharField(verbose_name="快照名字", max_length=128, help_text="沙箱初始化使用的快照（镜像）")

    target = models.CharField(verbose_name="目标区域", max_length=32, help_text="沙箱所属目标区域（集群）")
    env = models.JSONField(verbose_name="环境变量", default=dict)
    cpu = models.DecimalField(verbose_name="CPU 上限（核）", max_digits=10, decimal_places=2, default="2")
    memory = models.DecimalField(verbose_name="内存上限（GB）", max_digits=10, decimal_places=2, default="1")

    status = models.CharField(verbose_name="状态", max_length=16, default=SandboxStatus.PENDING.value)
    started_at = models.DateTimeField("启动时间", null=True)
    stopped_at = models.DateTimeField("停止时间", null=True)
    deleted_at = models.DateTimeField("删除时间", null=True)
    creator = BkUserField()
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("tenant_id", "name")
