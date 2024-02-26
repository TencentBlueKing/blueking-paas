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
import uuid
from typing import Optional

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
    def get_by_mount(self, m: "Mount"):
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


class PVCSourceManager(models.Manager):
    def get_by_mount(self, m: "Mount"):
        if not m.source_config.persistentVolumeClaim:
            raise ValueError(f"Mount {m.name} is invalid: source_config.persistentVolumeClaim is none")

        return self.get(
            application_id=m.module.application_id,
            environment_name=m.environment_name,
            name=m.source_config.persistentVolumeClaim.name,
        )


class PersistentVolumeClaimSource(TimestampedModel):
    """PVC 类型的挂载资源"""

    application_id = models.UUIDField(verbose_name=_("所属应用"), null=False)
    module_id = models.UUIDField(verbose_name=_("所属模块"), null=True)
    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_("挂载资源名"))
    storage = models.CharField(max_length=63)
    storage_class_name = models.CharField(max_length=63)

    objects = PVCSourceManager()

    class Meta:
        unique_together = ("name", "application_id", "environment_name")


class MountManager(models.Manager):
    def new(
        self,
        app_code: str,
        module_id: uuid.UUID,
        name: str,
        environment_name: str,
        mount_path: str,
        source_type: str,
        region: str,
        source_name: Optional[str] = None,
    ):
        # 根据 source_type 生成对应的 source_config
        from paas_wl.bk_app.cnative.specs.mounts import generate_source_config_name, init_source_controller

        source_config_name = source_name or generate_source_config_name(app_code=app_code)
        controller = init_source_controller(source_type)
        source_config = controller.new_volume_source(name=source_config_name)

        return Mount.objects.create(
            module_id=module_id,
            name=name,
            environment_name=environment_name,
            mount_path=mount_path,
            source_type=source_type,
            region=region,
            source_config=source_config,
        )


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

    objects = MountManager()

    class Meta:
        unique_together = ("module_id", "mount_path", "environment_name")
