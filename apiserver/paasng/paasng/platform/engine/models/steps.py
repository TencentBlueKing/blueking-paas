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

from typing import List

import jsonfield
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import CharField, DateTimeField, Serializer, SerializerMethodField
from translated_fields import TranslatedFieldWithFallback

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.exceptions import StepNotInPresetListError
from paasng.platform.engine.models import DeployPhaseTypes
from paasng.platform.engine.models.base import MarkStatusMixin
from paasng.platform.engine.models.phases import DeployPhase
from paasng.utils.models import AuditedModel, UuidAuditedModel


class DeployStepEventSLZ(Serializer):
    """Step SeverSendEvent"""

    phase = SerializerMethodField()
    name = CharField()
    start_time = DateTimeField(format="%Y-%m-%d %H:%M:%S", allow_null=True)
    complete_time = DateTimeField(format="%Y-%m-%d %H:%M:%S", allow_null=True)
    status = CharField(allow_null=True)

    def get_phase(self, obj) -> str:
        return obj.phase.type


class DeployStepMetaManager(models.Manager):
    def get_by_natural_key(self, phase, name):
        return self.get(phase=phase, name=name)


class DeployStepMeta(AuditedModel):
    """部署步骤元信息

    [multi-tenancy] This model is not tenant-aware.
    """

    phase = models.CharField(verbose_name=_("关联阶段"), max_length=16, choices=DeployPhaseTypes.get_choices())
    name = models.CharField(_("步骤名称"), db_index=True, max_length=32)
    display_name = TranslatedFieldWithFallback(models.CharField(_("步骤名称(展示用)"), max_length=64, null=True))

    started_patterns = jsonfield.JSONField(_("匹配规则"), default=[], null=True, blank=True)
    finished_patterns = jsonfield.JSONField(_("匹配规则"), default=[], null=True, blank=True)

    objects = DeployStepMetaManager()

    def __str__(self):
        return f"{self.phase}-{self.name}"

    class Meta:
        ordering = ["id"]

    def natural_key(self):
        return (self.phase, self.name)


class StepMetaSetManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class StepMetaSet(AuditedModel):
    """部署步骤元信息集

    [multi-tenancy] This model is not tenant-aware.
    """

    # Q: 为什么不从一个大的 StepMeta 池直接过滤 image 和 buildpack 获得一个 StepMeta 列表？为什么要额外增加一个模型？
    # A: StepMeta 之间可能没有绝对的顺序关系，需要用 StepMetaSet 定义

    name = models.CharField(_("步骤集名称"), max_length=32)
    metas = models.ManyToManyField(DeployStepMeta, "关联步骤元信息", default=[])
    is_default = models.BooleanField(_("是否为默认步骤集"), default=False)

    objects = StepMetaSetManager()

    def __str__(self):
        return f"{self.name}-default?{self.is_default}-metas({self.metas.all().count()})"

    def natural_key(self):
        return (self.name,)

    def create_step_instances(self, phase: "DeployPhase") -> List["DeployStep"]:
        instances = []
        for step_meta in self.list_metas_by_phase(DeployPhaseTypes(phase.type)):
            attrs = {"name": step_meta.name, "phase": phase, "meta": step_meta, "tenant_id": phase.tenant_id}
            for field in DeployStepMeta.display_name.fields:
                attrs[field] = getattr(step_meta, field)
            instances.append(DeployStep(**attrs))
        return DeployStep.objects.bulk_create(instances)

    def list_metas_by_phase(self, phase_type: DeployPhaseTypes) -> List[DeployStepMeta]:
        # Tips: StepMetaSet 与 DeployStepMeta 是 N-N 的关系, 这里借助中间表的自增 id 进行排序
        return [
            relationship.deploystepmeta
            for relationship in self.metas.through.objects.filter(
                deploystepmeta__phase=phase_type.value, stepmetaset_id=self.pk
            )
            .order_by("id")
            .prefetch_related("deploystepmeta")
        ]

    def list_sorted_step_names(self, phase_type: DeployPhaseTypes) -> List[str]:
        return list(
            self.metas.through.objects.filter(deploystepmeta__phase=phase_type.value, stepmetaset_id=self.pk)
            .order_by("id")
            .values_list("deploystepmeta__name", flat=True)
        )

    class Meta:
        ordering = ["id"]


# 声明要求确保了所有 DeployStepMeta 对象在任何 StepMetaSet 对象之前序列化
StepMetaSet.natural_key.dependencies = ["engine.DeployStepMeta"]  # type: ignore


class DeployStep(UuidAuditedModel, MarkStatusMixin):
    """部署步骤"""

    name = models.CharField(_("步骤名称"), db_index=True, max_length=32)
    display_name = TranslatedFieldWithFallback(models.CharField(_("步骤名称(展示用)"), max_length=64, null=True))
    phase = models.ForeignKey(DeployPhase, on_delete=models.CASCADE, verbose_name=_("关联阶段"), related_name="steps")
    skipped = models.BooleanField(_("是否跳过"), default=False)
    status = models.CharField(_("状态"), choices=JobStatus.get_choices(), null=True, max_length=32)
    start_time = models.DateTimeField(_("阶段开始时间"), null=True)
    complete_time = models.DateTimeField(_("阶段完成时间"), null=True)
    # 存量数据将不关联 meta
    meta = models.ForeignKey(
        DeployStepMeta, on_delete=models.CASCADE, verbose_name=_("元信息"), related_name="instances", null=True
    )

    tenant_id = tenant_id_field_factory()

    class Meta:
        ordering = ["created"]

    def ensure_start_before_complete(self):
        """保证事件的开始事件不晚于结束时间

        当状态检测存在并行竞争态，同时某些步骤的执行存在过快的情况
        DB 的状态更新速度会明显慢于内存事件的更新，此时 DB 的更新虽然能够保证准确
        但是竞争存储的中间态会被发送到 SSE 事件流中，影响前端步骤耗时判断
        所以在这里我们要手动保证中间态的正确性
        """
        if self.start_time and self.complete_time and self.start_time > self.complete_time:
            self.complete_time = self.start_time

    def to_dict(self):
        # 仅修改内存对象，不更新 DB
        self.ensure_start_before_complete()

        return DeployStepEventSLZ(self).data

    @property
    def is_completed(self) -> bool:
        return self.status in JobStatus.get_finished_states()

    def __str__(self):
        if not self.status:
            return f"Phase<{self.phase.type}>-{self.name}-Skip?<{self.skipped}>"
        else:
            return f"Phase<{self.phase.type}>-{self.name}-Status<{self.status}>"

    @classmethod
    def get_event_type(cls) -> str:
        return "step"

    def try_to_bind_meta(self) -> bool:
        """尝试通过步骤名为存量实例绑定元信息"""
        if self.meta:
            return False

        try:
            self.meta = DeployStepMeta.objects.get(name=self.name)
        except DeployStepMeta.DoesNotExist:
            raise StepNotInPresetListError(self.name)
        except DeployStepMeta.MultipleObjectsReturned:
            self.meta = DeployStepMeta.objects.filter(name=self.name)[0]

        self.save()
        return True
