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
from typing import TYPE_CHECKING, Dict, NamedTuple, Optional, Set

from blue_krill.models.fields import EncryptField
from django.db import models
from django.db.models import Case, IntegerField, Q, Value, When
from jsonfield import JSONField
from translated_fields import TranslatedField, TranslatedFieldWithFallback

from paasng.core.core.storages.object_storage import service_logo_storage
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.utils.models import ImageField, UuidAuditedModel

if TYPE_CHECKING:
    from django.db.models.query import QuerySet

    from paasng.accessories.services.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ServiceCategory(models.Model):
    """Service Category

    [multi-tenancy] This model is not tenant-aware.
    """

    name = TranslatedField(models.CharField("分类名称", max_length=64, unique=True))
    sort_priority = models.IntegerField("排序权重", default=0)

    def __str__(self):
        return self.name


class ServiceManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Service(UuidAuditedModel):
    """Service model for PaaS

    [multi-tenancy] This model is not tenant-aware.
    """

    name = models.CharField(verbose_name="服务名称", max_length=64, unique=True)
    display_name = TranslatedFieldWithFallback(models.CharField(verbose_name="服务全称", max_length=128))
    logo = ImageField(storage=service_logo_storage, upload_to="service-logo", verbose_name="服务logo", null=True)
    logo_b64 = models.TextField(verbose_name="服务 logo 的地址, 支持base64格式", null=True, blank=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, verbose_name="服务分类")
    description = TranslatedFieldWithFallback(models.CharField(verbose_name="服务简介", max_length=1024, blank=True))
    long_description = TranslatedFieldWithFallback(models.TextField(verbose_name="服务详细介绍", blank=True))
    instance_tutorial = TranslatedFieldWithFallback(models.TextField(verbose_name="服务markdown介绍", blank=True))
    available_languages = models.CharField(verbose_name="支持编程语言", max_length=1024, null=True, blank=True)
    config = JSONField(default={})
    is_active = models.BooleanField(verbose_name="是否可用", default=True)

    # When a service's "is_visible" was set to false, it will be hidden in application's service
    # index page. But an already existed binding relationship won't be affected.
    is_visible = models.BooleanField(verbose_name="是否可见", default=True)

    objects = ServiceManager()

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name

    def _get_service_vendor_instance(self, plan: "Plan") -> "BaseProvider":
        from paasng.accessories.services.providers import get_provider_cls_by_provider_name

        provider_cls = get_provider_cls_by_provider_name(self.provider_name)
        return provider_cls(config=plan.get_config())

    @staticmethod
    def format_credentials(raw_credentials: Dict, prefix: str, protected_keys: Optional[Set] = None) -> Dict:
        """Add prefix to all key of raw_credentials, and make sure all key is UpperCase.

        :param protected_keys: the keys in protected_keys will be skip format.

        >>> Service.format_credentials({'host': 'xxx', 'port': 80}, prefix='rabbitmq')
        {'RABBITMQ_HOST': 'xxx', 'RABBITMQ_PORT': 80}

        >>> Service.format_credentials({'host': 'xxx', 'port': 80}, prefix='rabbitmq', protected_keys={"host"})
        {'host': 'xxx', 'RABBITMQ_PORT': 80}
        """
        credentials = {}
        for raw_key, value in list(raw_credentials.items()):
            if protected_keys is None or raw_key not in protected_keys:
                key = "{prefix}_{key}".format(prefix=prefix, key=raw_key).upper()
            else:
                key = raw_key
            credentials[key] = value
        return credentials

    def create_service_instance_by_plan(self, plan, params: Dict) -> "ServiceInstance":
        """provision service instance"""
        # handler load config
        service_handler_instance = self._get_service_vendor_instance(plan)

        # provision
        raw_credentials, config = service_handler_instance.create(params=params)

        credentials = self.format_credentials(
            raw_credentials, prefix=self.name, protected_keys=service_handler_instance.protected_keys
        )
        service_instance_param = {
            "service": self,
            "credentials": json.dumps(credentials),
            "plan": plan,
            "tenant_id": plan.tenant_id,
        }
        if config:
            service_instance_param["config"] = config

        service_instance, _ = ServiceInstance.objects.get_or_create(**service_instance_param)  # noqa: F811
        return service_instance

    def delete_service_instance(self, service_instance: "ServiceInstance") -> None:
        # handler load config
        service_handler_instance = self._get_service_vendor_instance(service_instance.plan)

        # delete resource
        instance_data = InstanceData(
            credentials=json.loads(service_instance.credentials),
            config=service_instance.config,
        )
        logger.info(f"going to delete instance resource: {instance_data.credentials}")
        service_handler_instance.delete(instance_data)

        logger.info(f"going to delete service instance<{service_instance.uuid}> from db")
        service_instance.delete()

    def patch_service_instance_by_plan(self, plan, params) -> None:
        service_handler_instance = self._get_service_vendor_instance(plan)
        service_handler_instance.patch(params=params)

    @property
    def prefer_async_delete(self):
        """由于不是所有增强服务都实现了资源回收，所以默认都使用异步删除"""
        return self.config.get("prefer_async_delete", True)

    @property
    def provider_name(self):
        """获取供应商类型"""
        return self.config.get("provider_name", self.name)


class ServiceInstance(UuidAuditedModel):
    """
    specific info of service
    """

    service = models.ForeignKey("Service", on_delete=models.CASCADE)
    plan = models.ForeignKey("Plan", on_delete=models.CASCADE)
    config = JSONField(default={})
    credentials = EncryptField(default="")
    to_be_deleted = models.BooleanField(default=False)
    tenant_id = tenant_id_field_factory()

    def __str__(self):
        return "{service}-{plan}-{id}".format(service=repr(self.service), plan=repr(self.plan), id=self.uuid)


class PreCreatedInstance(UuidAuditedModel):
    """预创建的服务实例"""

    plan = models.ForeignKey("Plan", on_delete=models.SET_NULL, db_constraint=False, blank=True, null=True)
    config = JSONField(default=dict, help_text="same of ServiceInstance.config")
    credentials = EncryptField(default="", help_text="same of ServiceInstance.credentials")
    is_allocated = models.BooleanField(default=False, help_text="实例是否已被分配")
    tenant_id = tenant_id_field_factory()

    def acquire(self):
        self.is_allocated = True
        self.save(update_fields=["is_allocated"])

    def release(self):
        self.is_allocated = False
        self.save(update_fields=["is_allocated"])

    @classmethod
    def select_for_request(cls, plan: "Plan", params: Dict) -> Optional["PreCreatedInstance"]:
        """
        在指定 plan 下，根据 params 选择一个未分配的预创建实例
        params 若不包括 application_code, env, module_name, 则使用一般的 FIFO 策略进行匹配,
        并且会排除掉有具体绑定策略的实例

        :param params: 至少包含 application_code, env, module_name 三个字段中的一个或多个字段，用于匹配绑定策略
        """
        unallocated_qs = cls.objects.select_for_update().filter(plan=plan, is_allocated=False).order_by("created")

        policy_qs = PreCreatedInstanceBindingPolicy.objects.filter(pre_created_instance__in=unallocated_qs)
        without_policies_qs = unallocated_qs.exclude(
            pk__in=PreCreatedInstanceBindingPolicy.objects.values("pre_created_instance")
        )
        if not all(k in params for k in ("application_code", "env", "module_name")):
            logger.warning("missing params to match pre-created instance, use plain FIFO match strategy")
            return without_policies_qs.first()

        policy = PreCreatedInstanceBindingPolicy.resolve_policy(
            app_code=params["application_code"],
            module_name=params["module_name"],
            env=params["env"],
            policy_qs=policy_qs,
        )
        if not policy:
            logger.debug("no matching binding policy found, use plain FIFO match strategy")
            return unallocated_qs.first()

        return policy.pre_created_instance

    def __str__(self):
        return "{id}-{plan}".format(plan=repr(self.plan), id=self.uuid)


class PreCreatedInstanceBindingPolicy(UuidAuditedModel):
    pre_created_instance = models.ForeignKey(
        PreCreatedInstance,
        on_delete=models.CASCADE,
        db_constraint=False,
        blank=True,
        null=True,
        related_name="binding_policies",
    )
    app_code = models.CharField(max_length=20, null=True)
    module_name = models.CharField(max_length=20, null=True)
    env = models.CharField(max_length=16, null=True)

    tenant_id = tenant_id_field_factory(db_index=False)

    @classmethod
    def resolve_policy(
        cls, app_code, module_name, env, policy_qs: Optional["QuerySet"] = None
    ) -> Optional["PreCreatedInstanceBindingPolicy"]:
        """
        找到最匹配的绑定策略, 匹配优先级为 app_code > module_name > env, 可以认为是比较 (app_code, module_name, env) 的大小
        (app_code, module_name, env) 相同时, 返回 created_at 最早的那个

        :param policy_qs: 可选的 QuerySet, 用于指定查询范围
        """
        if not policy_qs:
            policy_qs = cls.objects.filter(pre_created_instance__isallocated=False)

        candidates = policy_qs.filter(
            Q(app_code=app_code) | Q(app_code__isnull=True),
            Q(module_name=module_name) | Q(module_name__isnull=True),
            Q(env=env) | Q(env__isnull=True),
        ).exclude(app_code__isnull=True, module_name__isnull=True, env__isnull=True)

        if not candidates.exists():
            return None

        match_weight = (
            Case(When(app_code=app_code, then=Value(3)), default=Value(0), output_field=IntegerField())
            + Case(When(module_name=module_name, then=Value(2)), default=Value(0), output_field=IntegerField())
            + Case(When(env=env, then=Value(1)), default=Value(0), output_field=IntegerField())
        )
        return candidates.annotate(match_weight=match_weight).order_by("-match_weight", "created").first()


class Plan(UuidAuditedModel):
    """
    Plan model
    contain provider and resource spec
    """

    service = models.ForeignKey("Service", on_delete=models.CASCADE)
    name = models.CharField("方案名称", max_length=64)
    description = models.CharField(verbose_name="方案简介", max_length=1024, blank=True)
    config = EncryptField(verbose_name="方案配置", default="")
    is_active = models.BooleanField(verbose_name="是否可用", default=True)
    tenant_id = tenant_id_field_factory(db_index=False)

    class Meta:
        unique_together = ("tenant_id", "service", "name")

    @property
    def is_eager(self):
        """PlanObj compatible property"""
        return False

    def __str__(self):
        return "{name}-{service}".format(name=self.name, service=self.service.name)

    def get_config(self) -> Dict:
        config = json.loads(self.config)
        config["__plan__"] = self
        return config


class ResourceId(models.Model):
    """[multi-tenancy] This model is not tenant-aware."""

    namespace = models.CharField(max_length=32)
    uid = models.CharField(max_length=64, null=False, unique=True, db_index=True)

    class Meta:
        unique_together = ("namespace", "uid")

    def __str__(self):
        return "{ns}-{id}".format(ns=self.namespace, id=self.uid)


class InstanceData(NamedTuple):
    credentials: Dict
    # NOTE: config
    # admin_url: will show admin entrance to developer
    # is_pre_created: whether this instance is pre-created（PreCreatedInstance）
    # provider_name: the provider name of this instance（service.provider_name / mysql / rabbitmq ...)
    # enable_tls: whether this instance enable tls (must deploy with tls cert secrets)
    config: Optional[Dict] = None
