# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import json
import logging
from typing import TYPE_CHECKING, Dict, NamedTuple, Optional, Set

from blue_krill.models.fields import EncryptField
from django.db import models
from jsonfield import JSONField
from translated_fields import TranslatedField, TranslatedFieldWithFallback

from paasng.core.core.storages.object_storage import service_logo_storage
from paasng.utils.models import ImageField, UuidAuditedModel

if TYPE_CHECKING:
    from paasng.accessories.services.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ServiceCategory(models.Model):
    """
    Service Category
    """

    name = TranslatedField(models.CharField("分类名称", max_length=64, unique=True))
    sort_priority = models.IntegerField("排序权重", default=0)

    def __str__(self):
        return self.name


class ServiceManager(models.Manager):
    def get_by_natural_key(self, region, name):
        return self.get(region=region, name=name)


class Service(UuidAuditedModel):
    """
    Service model for PaaS
    """

    region = models.CharField(max_length=32)
    name = models.CharField(verbose_name="服务名称", max_length=64)
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

    class Meta:
        unique_together = ("region", "name")

    def natural_key(self):
        return (self.region, self.name)

    def __str__(self):
        return "{name}-{region}".format(name=self.name, region=self.region)

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
        service_instance_param = {"service": self, "credentials": json.dumps(credentials), "plan": plan}
        if config:
            service_instance_param["config"] = config

        service_instance, _ = ServiceInstance.objects.get_or_create(**service_instance_param)
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

    def __str__(self):
        return "{service}-{plan}-{id}".format(service=repr(self.service), plan=repr(self.plan), id=self.uuid)


class PreCreatedInstance(UuidAuditedModel):
    """预创建的服务实例"""

    plan = models.ForeignKey("Plan", on_delete=models.SET_NULL, db_constraint=False, blank=True, null=True)
    config = JSONField(default=dict, help_text="same of ServiceInstance.config")
    credentials = EncryptField(default="", help_text="same of ServiceInstance.credentials")
    is_allocated = models.BooleanField(default=False, help_text="实例是否已被分配")

    def acquire(self):
        self.is_allocated = True
        self.save(update_fields=["is_allocated"])

    def release(self):
        self.is_allocated = False
        self.save(update_fields=["is_allocated"])

    def __str__(self):
        return "{id}-{plan}".format(plan=repr(self.plan), id=self.uuid)


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

    class Meta:
        unique_together = ("service", "name")

    @property
    def is_eager(self):
        """PlanObj compatible property"""
        return False

    def __str__(self):
        return "{name}-{service}-{region}".format(
            name=self.name, service=self.service.name, region=self.service.region
        )

    def get_config(self) -> Dict:
        config = json.loads(self.config)
        config["__plan__"] = self
        return config


class ResourceId(models.Model):
    namespace = models.CharField(max_length=32)
    uid = models.CharField(max_length=64, null=False, unique=True, db_index=True)

    class Meta:
        unique_together = ("namespace", "uid")

    def __str__(self):
        return "{ns}-{id}".format(ns=self.namespace, id=self.uid)


class InstanceData(NamedTuple):
    credentials: Dict
    # NOTE: config
    # - if admin_url in config, will show admin entrance to developer
    config: Optional[Dict] = None
