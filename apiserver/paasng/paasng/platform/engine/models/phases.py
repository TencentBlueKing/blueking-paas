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

from typing import TYPE_CHECKING, Dict

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import CharField, DateTimeField, Serializer

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.exceptions import DuplicateNameInSamePhaseError, StepNotInPresetListError
from paasng.platform.engine.models import Deployment, EngineApp, MarkStatusMixin
from paasng.utils.models import UuidAuditedModel

if TYPE_CHECKING:
    from paasng.platform.engine.models.steps import DeployStep


class DeployPhaseTypes(StrStructuredEnum):
    """部署阶段"""

    PREPARATION = EnumField("preparation", label=_("准备阶段"))
    BUILD = EnumField("build", label=_("构建阶段"))
    RELEASE = EnumField("release", label=_("部署阶段"))


class DeployPhaseEventSLZ(Serializer):
    """Phase SeverSendEvent"""

    name = CharField(source="type")
    start_time = DateTimeField(format="%Y-%m-%d %H:%M:%S", allow_null=True)
    complete_time = DateTimeField(format="%Y-%m-%d %H:%M:%S", allow_null=True)
    status = CharField(allow_null=True)


class DeployPhase(UuidAuditedModel, MarkStatusMixin):
    """部署阶段"""

    type = models.CharField(_("部署阶段类型"), choices=DeployPhaseTypes.get_choices(), max_length=32)
    engine_app = models.ForeignKey(EngineApp, on_delete=models.CASCADE, verbose_name=_("关联引擎应用"), null=False)
    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, verbose_name=_("关联部署操作"), null=True)
    status = models.CharField(_("状态"), choices=JobStatus.get_choices(), null=True, max_length=32)
    start_time = models.DateTimeField(_("阶段开始时间"), null=True)
    complete_time = models.DateTimeField(_("阶段完成时间"), null=True)

    tenant_id = tenant_id_field_factory()

    class Meta:
        ordering = ["created"]

    @property
    def attached(self) -> bool:
        """是否关联了 deployment 对象"""
        # 如果没有关联 deployment 对象，说明是下一次部署的 phase 对象
        return bool(self.deployment)

    def _get_step_pattern_map(self, pattern_type: str) -> Dict[str, str]:
        """获取关联的步骤和匹配字符串集"""
        step_pattern_map: Dict[str, str] = {}
        for step_name, patterns in self.steps.select_related("meta").all().values_list("name", pattern_type):
            # 防御 meta 未关联的情况
            if patterns is None:
                continue

            # 在不同步骤间定义 pattern 时就需要保证去重，否则会被后定义的 pattern 覆盖
            for pattern in patterns:  # type: str
                step_pattern_map[pattern] = step_name

        return step_pattern_map

    def get_started_pattern_map(self) -> Dict:
        return self._get_step_pattern_map("meta__started_patterns")

    def get_finished_pattern_map(self) -> Dict:
        return self._get_step_pattern_map("meta__finished_patterns")

    def get_step_by_name(self, name: str) -> "DeployStep":
        """通过步骤名获取步骤实例"""
        try:
            # 由于同一个 phase 内的 step 原则上是不能同名的，所以可以直接 get
            return self.steps.get(name=name)
        except ObjectDoesNotExist:
            raise StepNotInPresetListError(name)
        except MultipleObjectsReturned:
            raise DuplicateNameInSamePhaseError(name)

    def attach(self, deployment: Deployment):
        if self.attached:
            return

        self.deployment = deployment
        self.save(update_fields=["deployment", "updated"])

    def get_unfinished_steps(self):
        """获取所有未结束的步骤"""
        return self.steps.filter(status=JobStatus.PENDING.value)

    def to_dict(self):
        return DeployPhaseEventSLZ(self).data

    @classmethod
    def get_event_type(cls) -> str:
        return "phase"

    def __str__(self):
        if self.deployment:
            return f"App<{self.engine_app.name}>-Phase<{self.type}>-Deployment<{self.deployment.pk}>"
        else:
            return f"App<{self.engine_app.name}>-Phase<{self.type}>"
