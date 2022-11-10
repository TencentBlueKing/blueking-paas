# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import json
from contextlib import contextmanager
from copy import deepcopy
from enum import Enum
from typing import Callable

from blue_krill.models.fields import EncryptField
from django.db import models
from django.utils.functional import cached_property
from jsonfield import JSONField
from paas_service.models import AuditedModel, UuidAuditedModel

from .constants import LinkType


class Tag(AuditedModel):
    class Meta(object):
        abstract = True

    instance: 'models.Model'
    key = models.CharField("名称", max_length=64)
    value = models.CharField("值", max_length=128)


class Cluster(AuditedModel):
    name = models.CharField("名称", max_length=64)
    host = models.CharField("主机", max_length=64)
    port = models.IntegerField("端口", default=5672)
    management_api = models.TextField("管理地址")
    admin = models.CharField("管理员", max_length=64)
    password = EncryptField(verbose_name="密码")
    version = models.CharField("版本", max_length=16)
    enable = models.BooleanField("是否启用", default=True)
    extra = JSONField("额外信息", default=dict, blank=True, null=True)

    def __str__(self):
        return f"{self.name}[{self.pk}]"


class ClusterTag(Tag):
    """集群标签，用于分配和分组"""

    instance = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name="tags")


class LinkableModel(AuditedModel):
    class Meta(object):
        abstract = True

    link_type = models.IntegerField(
        "连接方式", default=LinkType.empty.value, choices=[(i.value, i.name) for i in LinkType]
    )
    linked = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, default=None)

    def resolve_extend(self, other: 'LinkableModel'):
        """处理继承连接合并细节"""
        for field in self._meta.fields:
            attname = field.attname
            value = getattr(other, attname, None)
            if value is not None:
                setattr(self, attname, value)

    @cached_property
    def resolved(self):
        """解决连接关系"""
        if self.linked is None:  # 根对象
            resolved = deepcopy(self)
            resolved.pk = None
            return resolved

        resolved = self.linked.resolved  # 默认代理模式

        if self.link_type == LinkType.inherit.value:  # 继承需要修改
            resolved.resolve_extend(self)

        return resolved


class PolicyTarget(Enum):
    all = "all"  # exchanges and queues
    exchanges = "exchanges"
    queues = "queues"


class UserPolicy(LinkableModel):
    """集群下创建 vhost 默认策略，和具体 vhost 无关"""

    resolve_link: Callable[[], 'UserPolicy']

    name = models.CharField("名称", max_length=64, null=True)
    enable = models.BooleanField("是否启用", default=True)
    pattern = models.CharField("匹配模式", max_length=128, null=True, blank=True)
    apply_to = models.CharField(
        "应用对象", choices=[(i.value, i.name) for i in PolicyTarget], null=True, blank=True, max_length=64
    )
    priority = models.IntegerField("优先级", null=True, blank=True)
    definitions = JSONField("策略定义", default=None, null=True, blank=True)
    cluster_id = models.IntegerField("集群id", blank=True, default=None)

    @cached_property
    def cluster(self) -> 'Cluster':
        return Cluster.objects.filter(pk=self.cluster_id)

    def resolve_extend(self, other: 'UserPolicy'):
        definitions = self.definitions or {}
        definitions.update(other.definitions or {})
        super().resolve_extend(other)
        self.definitions = definitions

    def dict(self):
        resolved = self.resolved
        return {
            "name": resolved.name,
            "pattern": resolved.pattern,
            "apply-to": resolved.apply_to,
            "definition": resolved.definitions or {},
            "priority": resolved.priority,
        }

    def __str__(self):
        return f"{self.name}[{self.pk}]"


class UserPolicyTag(Tag):
    """表示绑定关系"""

    instance = models.ForeignKey(UserPolicy, on_delete=models.CASCADE, related_name="tags")


class LimitType(Enum):
    max_connections = "max-connections"
    max_queues = "max-queues"


class LimitPolicy(LinkableModel):
    """集群下创建 vhost 限制机制，和具体 vhost 无关"""

    resolve_link: Callable[[], 'LimitPolicy']

    name = models.CharField("名称", max_length=64, null=True)
    enable = models.BooleanField("是否启用", default=True)
    limit = models.CharField(
        "限制类型", choices=[(i.value, i.name) for i in LimitType], null=True, blank=True, max_length=64
    )
    value = models.IntegerField("限制值", null=True, blank=True)
    cluster_id = models.IntegerField("集群id", blank=True, default=None)

    @cached_property
    def cluster(self) -> 'Cluster':
        return Cluster.objects.filter(pk=self.cluster_id)

    def __str__(self):
        return f"{self.name}[{self.pk}]"


class LimitPolicyTag(Tag):
    """表示绑定关系"""

    instance = models.ForeignKey(LimitPolicy, on_delete=models.CASCADE, related_name="tags")


class InstanceBill(UuidAuditedModel):
    """实例单据，保存申请上下文，方便重入"""

    name = models.CharField("应用名称", max_length=128)
    action = models.CharField("申请动作", max_length=32)
    context = EncryptField(verbose_name="上下文", default="{}")

    def get_context(self):
        return json.loads(self.context or "{}")

    def set_context(self, context: 'dict'):
        self.context = json.dumps(context)

    @contextmanager
    def log_context(self) -> 'dict':
        context = self.get_context()
        try:
            yield context
        finally:
            self.set_context(context)
            self.save()
