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
from django.utils.translation import gettext_lazy as _

from paas_wl.utils.models import UuidAuditedModel
from paasng.core.tenant.fields import tenant_id_field_factory

from .smart_build import SmartBuildRecord


class SmartBuildPhase(UuidAuditedModel):
    """[暂未使用, 后续有需求将启用] s-mart 构建阶段"""

    # 枚举值 -> SmartBuildPhaseType.
    type = models.CharField(_("构建阶段类型"), max_length=32)
    smart_build = models.ForeignKey(
        SmartBuildRecord,
        on_delete=models.CASCADE,
        verbose_name=_("关联的构建记录"),
        null=True,
        related_name="phases",
        db_constraint=False,
    )
    # 枚举值 -> JobStatus. null 表示未设置
    status = models.CharField(_("状态"), null=True, max_length=32)
    start_time = models.DateTimeField(_("阶段开始时间"), null=True)
    complete_time = models.DateTimeField(_("阶段完成时间"), null=True)

    tenant_id = tenant_id_field_factory()

    class Meta:
        ordering = ["created"]
        unique_together = (("smart_build", "type"),)
