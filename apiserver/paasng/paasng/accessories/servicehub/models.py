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

import json
import logging
from typing import Collection, Dict

from django.db import models

from paasng.accessories.servicehub.constants import ServiceAllocationPolicyType, ServiceType
from paasng.accessories.servicehub.services import ServiceObj
from paasng.accessories.services.models import Plan, Service, ServiceInstance
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.applications.models import ApplicationEnvironment
from paasng.platform.modules.models import Module
from paasng.utils.models import AuditedModel, OwnerTimestampedModel, TimestampedModel, UuidAuditedModel

logger = logging.getLogger(__name__)


class ServiceModuleAttachment(OwnerTimestampedModel):
    """Module <-> Local Service relationship"""

    module = models.ForeignKey("modules.Module", on_delete=models.CASCADE, verbose_name="蓝鲸应用模块")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("service", "module")

    def __str__(self):
        return f"{self.service_id}-{self.module_id}"


class ServiceEngineAppAttachment(OwnerTimestampedModel):
    """
    engine app bind to service instance and plan
    """

    engine_app = models.ForeignKey("engine.EngineApp", on_delete=models.CASCADE, related_name="service_attachment")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    service_instance = models.ForeignKey(
        ServiceInstance, on_delete=models.CASCADE, null=True, blank=True, related_name="service_attachment"
    )
    credentials_enabled = models.BooleanField(default=True, verbose_name="是否使用凭证")
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("service", "engine_app")

    def create_service_instance(self) -> ServiceInstance:
        """create service instance, called by engine part when deploying"""
        if self.service_instance:
            return self.service_instance

        application_environment = ApplicationEnvironment.objects.get(engine_app=self.engine_app)
        params = {
            "engine_app_name": self.engine_app.name,
            "region": self.engine_app.region,
            "application_code": application_environment.application.code,
            "application_id": application_environment.application.id,
        }

        service_instance = self.service.create_service_instance_by_plan(self.plan, params=params)

        self.service_instance = service_instance
        self.save()
        return service_instance

    def bind_service_instance(self, credentials: Dict, config: Dict) -> ServiceInstance:
        """create service instance with the existing config and credentials, without calling provision"""
        service_instance = ServiceInstance.objects.create(
            service=self.service,
            plan=self.plan,
            credentials=json.dumps(credentials),
            config=config,
            tenant_id=self.plan.tenant_id,
        )
        self.service_instance = service_instance
        self.save(update_fields=["service_instance"])
        return service_instance

    def unbind_service_instance(self):
        """Unbind the instance without reclaiming resources."""
        if self.service_instance:
            self.service_instance.delete()
        super().delete()

    def delete(self, *args, **kwargs):
        """根据配置删除 或者 标记删除"""
        # 并未申请资源，直接删除 DB 记录
        if self.service_instance:
            self.clean_service_instance()
        super().delete(*args, **kwargs)

    def clean_service_instance(self):
        """回收增强服务资源"""
        if self.service.prefer_async_delete:
            self.service_instance.to_be_deleted = True
            self.service_instance.save()
            self.service_instance = None
            self.save()
        else:
            self.service.delete_service_instance(self.service_instance)

    def __str__(self):
        prefix = "{engine}-{service}-{plan}".format(
            engine=self.engine_app.name, service=self.service.name, plan=self.plan.name
        )

        if self.service_instance:
            return "{prefix}-{instance}".format(prefix=prefix, instance=self.service_instance)
        else:
            return "{prefix}-no-provision".format(prefix=prefix)


class UnboundServiceEngineAppAttachment(OwnerTimestampedModel):
    """Attachments between local service and engine application that are no longer bound,
    these instances behave like a temporary record so that the user or platform can recycle
    the associated resources later.
    """

    engine_app = models.ForeignKey(
        "engine.EngineApp",
        on_delete=models.CASCADE,
        db_constraint=False,
        verbose_name="蓝鲸引擎应用",
        related_name="unbound_service_attachment",
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE, db_constraint=False, verbose_name="增强服务")
    service_instance = models.ForeignKey(
        ServiceInstance,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_constraint=False,
        verbose_name="增强服务实例",
    )
    tenant_id = tenant_id_field_factory()

    class Meta:
        verbose_name = "unbound attachment between local service and engine app"
        unique_together = ("service", "engine_app", "service_instance")

    def clean_service_instance(self):
        """回收增强服务资源"""
        self.service.delete_service_instance(self.service_instance)


class RemoteServiceModuleAttachment(OwnerTimestampedModel):
    """Binding relationship of module <-> remote service"""

    module = models.ForeignKey("modules.Module", on_delete=models.CASCADE, verbose_name="蓝鲸应用模块")
    service_id = models.UUIDField(verbose_name="远程增强服务 ID")
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("service_id", "module")

    def __str__(self):
        return f"{self.service_id}-{self.module_id}"


class RemoteServiceEngineAppAttachment(OwnerTimestampedModel):
    """Binding relationship of engine app <-> remote service plan"""

    engine_app = models.ForeignKey(
        "engine.EngineApp", on_delete=models.CASCADE, related_name="remote_service_attachment"
    )
    service_id = models.UUIDField(verbose_name="远程增强服务 ID")
    plan_id = models.UUIDField(verbose_name="远程增强服务 Plan ID")
    service_instance_id = models.UUIDField(null=True)
    credentials_enabled = models.BooleanField(default=True, verbose_name="是否使用凭证")
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("service_id", "engine_app")


class UnboundRemoteServiceEngineAppAttachment(OwnerTimestampedModel):
    """Attachments between remote service and engine application that are no longer bound,
    these instances behave like a temporary record so that the user or platform can recycle
    the associated resources later.
    """

    engine_app = models.ForeignKey(
        "engine.EngineApp",
        on_delete=models.CASCADE,
        db_constraint=False,
        verbose_name="蓝鲸引擎应用",
        related_name="unbound_remote_service_attachment",
    )
    service_id = models.UUIDField(verbose_name="远程增强服务 ID")
    service_instance_id = models.UUIDField(null=True, verbose_name="远程增强服务实例 ID")
    tenant_id = tenant_id_field_factory()

    class Meta:
        verbose_name = "unbound attachment between remote service and engine app"
        unique_together = ("service_id", "engine_app", "service_instance_id")


class ServiceDBProperties:
    """Storing service related database properties"""

    col_service_type: str = ""
    model_module_rel: models.Model


class LocalServiceDBProperties(ServiceDBProperties):
    col_service_type = ServiceType.LOCAL
    model_module_rel = ServiceModuleAttachment


class RemoteServiceDBProperties(ServiceDBProperties):
    col_service_type = ServiceType.REMOTE
    model_module_rel = RemoteServiceModuleAttachment


class SharedServiceAttachmentManager(models.Manager):
    """Custom manager for SharedServiceAttachment model"""

    def list_by_ref_module(self, service: ServiceObj, module: Module) -> "Collection[SharedServiceAttachment]":
        """Get SharedServiceAttachment objects which reference given module and service object"""
        from paasng.accessories.servicehub.manager import get_db_properties

        db_props = get_db_properties(service)
        try:
            attachment = db_props.model_module_rel.objects.get(module_id=module.id, service_id=service.uuid)
        except db_props.model_module_rel.DoesNotExist:
            return []

        qs = self.get_queryset().filter(
            service_type=db_props.col_service_type,
            service_id=service.uuid,
            ref_attachment_pk=attachment.pk,
        )
        return qs


class SharedServiceAttachment(TimestampedModel):
    """Share a service binding relationship from other modules"""

    module = models.ForeignKey("modules.Module", on_delete=models.CASCADE, verbose_name="发起共享的应用模块")
    service_type = models.CharField(verbose_name="增强服务类型", max_length=16)
    service_id = models.UUIDField(verbose_name="增强服务 ID")
    ref_attachment_pk = models.IntegerField(verbose_name="被共享的服务绑定关系主键")
    tenant_id = tenant_id_field_factory()

    objects = SharedServiceAttachmentManager()

    class Meta:
        unique_together = ("module", "service_type", "service_id")


class ServiceAllocationPolicyManager(models.Manager):
    """The custom manager for ServiceAllocationPolicy model, provide shortcut methods."""

    def get_type(self, service: ServiceObj, tenant_id: str) -> ServiceAllocationPolicyType:
        """Get the allocation type by service.

        :return: the allocation type, use UNIFORM when the policy object does not exist.
        """
        try:
            obj = self.get_queryset().get(service_id=service.uuid, tenant_id=tenant_id)
        except ServiceAllocationPolicy.DoesNotExist:
            return ServiceAllocationPolicyType.UNIFORM
        return ServiceAllocationPolicyType(obj.type)

    def set_type_uniform(self, service: ServiceObj, tenant_id: str):
        """Set the allocation type to UNIFORM for the given service."""
        self.get_queryset().update_or_create(
            service_id=service.uuid,
            tenant_id=tenant_id,
            defaults={"type": ServiceAllocationPolicyType.UNIFORM.value},
        )

    def set_type_rule_based(self, service: ServiceObj, tenant_id: str):
        """Set the allocation type to RULE_BASED for the given service."""
        self.get_queryset().update_or_create(
            service_id=service.uuid,
            tenant_id=tenant_id,
            defaults={"type": ServiceAllocationPolicyType.RULE_BASED.value},
        )


class ServiceAllocationPolicy(UuidAuditedModel):
    """服务分配策略"""

    service_id = models.UUIDField(verbose_name="增强服务 ID", db_index=True)
    # 枚举值 -> ServiceAllocationPolicyType
    type = models.CharField(max_length=32, help_text="分配策略类型")

    tenant_id = tenant_id_field_factory()

    objects = ServiceAllocationPolicyManager()

    class Meta:
        unique_together = ("tenant_id", "service_id")


class ServiceBindingPolicy(AuditedModel):
    """统一分配策略。

    - 当前支持两类策略：静态和分环境，详见 ServiceBindingPolicyType。
    """

    service_id = models.UUIDField(verbose_name="增强服务 ID")
    # See `ServiceType` in constants
    service_type = models.CharField(verbose_name="增强服务类型", max_length=16, help_text="远程或本地")

    # See `ServiceBindingPolicyType`
    type = models.CharField(verbose_name="策略类型", max_length=16)
    data = models.JSONField(help_text="策略数据", default={})
    tenant_id = tenant_id_field_factory(db_index=False)

    class Meta:
        unique_together = ("tenant_id", "service_id")


class ServiceBindingPrecedencePolicy(AuditedModel):
    """按规则匹配，一般由多个 ServiceBindingPrecedencePolicy 实例组合形成一个完整的规则匹配。

    - 当前支持三种规则匹配：Region.in Cluster.in 和 AlwaysMatch，详见 PrecedencePolicyCondType。
    - 当前支持两类策略：静态和分环境，详见 ServiceBindingPolicyType。
    """

    service_id = models.UUIDField(verbose_name="增强服务 ID", db_index=True)
    # See `ServiceType` in constants
    service_type = models.CharField(verbose_name="增强服务类型", max_length=16, help_text="远程或本地")

    # See `PrecedencePolicyCondType`
    cond_type = models.CharField(verbose_name="条件类型", max_length=16)
    cond_data = models.JSONField(verbose_name="条件值", default={})
    # See `ServiceBindingPolicyType`
    type = models.CharField(verbose_name="策略类型", max_length=16)
    data = models.JSONField(help_text="策略值", default={})

    priority = models.SmallIntegerField(verbose_name="优先级", default=0, help_text="值越大，优先级越高")
    tenant_id = tenant_id_field_factory(db_index=False)

    class Meta:
        unique_together = ("tenant_id", "service_id", "priority")


class DefaultPolicyCreationRecord(AuditedModel):
    """[multi-tenancy] This model is not tenant-aware.
    默认租户下增强服务默认绑定策略创建记录

    功能说明：
    1. 记录默认租户下增强服务的策略初始化状态
    2. 当默认租户的增强服务创建 plan 后，平台会自动创建绑定策略（仅执行一次）
    3. 用户手动删除已创建的策略后，由于本表中已经有初始化记录保证不会重复初始化
    """

    service_id = models.UUIDField(verbose_name="增强服务 ID", unique=True)
    # See `ServiceType` in constants
    service_type = models.CharField(verbose_name="增强服务类型", max_length=16, help_text="远程或本地")
    finished_at = models.DateTimeField(verbose_name="完成时间", null=True, blank=True)
