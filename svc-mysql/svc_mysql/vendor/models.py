# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from blue_krill.models.fields import EncryptField
from django.db import models
from jsonfield import JSONField
from paas_service.fields import tenant_id_field_factory
from paas_service.models import UuidAuditedModel


class PlanMigrationStatus(models.TextChoices):
    """plan 迁移记录的状态。一条实例同时最多只有一条 prepared。"""

    PREPARED = "prepared", "已预分配"
    SWITCHED = "switched", "已切换"


class PlanMigration(UuidAuditedModel):
    """一次 MySQL 实例从源 plan 到目标 plan 的迁移。

    prepare 只创建目标库并记下凭证，不改 ServiceInstance。
    switch 把目标凭证写回原实例，uuid 不变。
    revert 把 switch 时记下的旧凭证写回去，状态回到 prepared，目标库保留。
    """

    instance = models.ForeignKey(
        "paas_service.ServiceInstance",
        verbose_name="服务实例",
        related_name="plan_migrations",
        on_delete=models.CASCADE,
    )
    app_code = models.CharField("应用 ID", max_length=64)
    module = models.CharField("模块", max_length=64, blank=True, default="")
    environment = models.CharField("环境", max_length=32)
    developer = models.CharField("开发者", max_length=128, blank=True, default="")

    source_plan = models.ForeignKey(
        "paas_service.Plan",
        verbose_name="源方案",
        related_name="+",
        on_delete=models.PROTECT,
    )
    target_plan = models.ForeignKey(
        "paas_service.Plan",
        verbose_name="目标方案",
        related_name="+",
        on_delete=models.PROTECT,
    )
    source_credentials = EncryptField(verbose_name="源库凭证")
    target_credentials = EncryptField(verbose_name="目标库凭证")
    source_config = JSONField("源实例配置", default=dict, blank=True)
    target_config = JSONField("目标实例配置", default=dict, blank=True)

    status = models.CharField("状态", max_length=16, choices=PlanMigrationStatus.choices)
    switched_at = models.DateTimeField("切换时间", null=True, blank=True)
    tenant_id = tenant_id_field_factory()

    class Meta:
        verbose_name = "方案迁移"
        verbose_name_plural = "方案迁移"
        indexes = [
            models.Index(fields=["app_code", "status"]),
            models.Index(fields=["instance", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.app_code}/{self.module}/{self.environment} {self.status}"
