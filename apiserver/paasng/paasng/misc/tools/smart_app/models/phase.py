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
from typing import TYPE_CHECKING, Any, Dict

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import CharField, DateTimeField, Serializer

from paas_wl.utils.models import UuidAuditedModel
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.exceptions import DuplicateNameInSamePhaseError, StepNotInPresetListError

from .smart_build import SmartBuildRecord

if TYPE_CHECKING:
    from paasng.misc.tools.smart_app.output import SmartBuildStream

    from .step import SmartBuildStep

logger = logging.getLogger(__name__)


class SmartBuildPhaseEventSLZ(Serializer):
    """Phase Event"""

    name = CharField(source="type")
    start_time = DateTimeField(format="%Y-%m-%d %H:%M:%S", allow_null=True)
    complete_time = DateTimeField(format="%Y-%m-%d %H:%M:%S", allow_null=True)
    status = CharField(allow_null=True)


class SmartBuildPhase(UuidAuditedModel):
    """s-mart 构建阶段"""

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

    @classmethod
    def get_event_type(cls) -> str:
        return "phase"

    def to_dict(self) -> Dict[str, Any]:
        return SmartBuildPhaseEventSLZ(self).data

    def get_step_by_name(self, name: str) -> "SmartBuildStep":
        """通过步骤名获取步骤实例"""
        try:
            # 同一个 phase 内的 step 原则上不能同名, 可以直接 get
            return self.steps.get(name=name)
        except ObjectDoesNotExist:
            raise StepNotInPresetListError(name)
        except MultipleObjectsReturned:
            raise DuplicateNameInSamePhaseError(name)

    def get_unfinished_steps(self) -> models.QuerySet["SmartBuildStep"]:
        """获取所有未结束的步骤"""
        return self.steps.filter(status=JobStatus.PENDING.value)

    def mark_procedure_status(self, status: JobStatus):
        """针对拥有 complete_time 和 start_time 的应用标记其状态"""
        update_fields = ["status", "updated"]
        now = timezone.localtime(timezone.now())

        if status in JobStatus.get_finished_states():
            self.complete_time = now
            update_fields.append("complete_time")

            # 步骤完成地过于快速，PaaS 来不及判断其开始就已经收到了结束的标志
            if not self.start_time and not self.status:
                self.start_time = now
                update_fields.append("start_time")
        else:
            self.start_time = now
            update_fields.append("start_time")

        self.status = status.value
        self.save(update_fields=update_fields)

    def mark_and_write_to_stream(self, stream: "SmartBuildStream", status: JobStatus, extra_info: Dict | None = None):
        """标记状态，并写到 stream"""
        self.mark_procedure_status(status)
        detail = self.to_dict()
        detail.update(extra_info or {})

        stream.write_event(self.get_event_type(), detail)
