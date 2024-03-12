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
from django.db import models
from django.utils.translation import gettext_lazy as _

from paas_wl.bk_app.applications.relationship import ModuleAttrFromID
from paas_wl.bk_app.cnative.specs.constants import (
    MountEnvName,
    VolumeSourceType,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.utils.models import TimestampedModel
from paasng.utils.models import make_json_field

SourceConfigField = make_json_field("SourceConfigField", VolumeSource)


class ConfigMapSourceManager(models.Manager):
    def get_by_mount(self, m: "Mount") -> "ConfigMapSource":
        """
        根据传入的 Mount 对象查找对应的 configmap 资源

        :param m: Mount object
        :return ConfigMapSource: 与传入的 Mount 对象对应的 configmap 资源
        :raises ValueError: 如果未传入 source_config.configMap
        """
        if not m.source_config.configMap:
            raise ValueError(f"Mount {m.name} is invalid: source_config.configMap is none")
        return self.get(
            application_id=m.module.application_id,
            environment_name=m.environment_name,
            name=m.source_config.configMap.name,
        )


class ConfigMapSource(TimestampedModel):
    """ConfigMap 类型的挂载资源"""

    application_id = models.UUIDField(verbose_name=_("所属应用"), null=False)
    module_id = models.UUIDField(verbose_name=_("所属模块"), null=True)
    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_("挂载资源名"))
    data = models.JSONField(default=dict)

    objects = ConfigMapSourceManager()

    class Meta:
        unique_together = ("name", "application_id", "environment_name")


class PersistentStorageManager(models.Manager):
    def get_by_mount(self, m: "Mount") -> "PersistentStorageSource":
        """
        根据传入的 Mount 对象查找对应的持久存储资源

        :param m: Mount object
        :return PersistentStorageSource: 与传入的 Mount 对象对应的持久存储资源
        :raises ValueError: 如果未传入 source_config.persistentStorage
        """
        if not m.source_config.persistentStorage:
            raise ValueError(f"Mount {m.name} is invalid: source_config.persistentStorage is none")

        return self.get(
            application_id=m.module.application_id,
            environment_name=m.environment_name,
            name=m.source_config.persistentStorage.name,
        )


class PersistentStorageSource(TimestampedModel):
    """持久存储类型的挂载资源"""

    application_id = models.UUIDField(verbose_name=_("所属应用"), null=False)
    module_id = models.UUIDField(verbose_name=_("所属模块"), null=True)
    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_("挂载资源名"))
    storage_size = models.CharField(max_length=63)
    storage_class_name = models.CharField(max_length=63)

    objects = PersistentStorageManager()

    class Meta:
        unique_together = ("name", "application_id", "environment_name")


class Mount(TimestampedModel):
    """挂载配置"""

    module_id = models.UUIDField(verbose_name=_("所属模块"), null=False)
    module = ModuleAttrFromID()

    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_("挂载点的名称"))
    mount_path = models.CharField(max_length=128)
    source_type = models.CharField(choices=VolumeSourceType.get_choices(), max_length=32)
    source_config: VolumeSource = SourceConfigField()

    class Meta:
        unique_together = ("module_id", "mount_path", "environment_name")
