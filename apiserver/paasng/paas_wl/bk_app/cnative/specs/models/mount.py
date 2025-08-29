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

from paas_wl.bk_app.applications.relationship import ModuleAttrFromID
from paas_wl.bk_app.cnative.specs.constants import (
    MountEnvName,
    VolumeSourceType,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.utils.models import TimestampedModel
from paasng.utils.models import make_json_field

SourceConfigField = make_json_field("SourceConfigField", VolumeSource)


class ConfigMapSource(TimestampedModel):
    """ConfigMap 类型的挂载资源

    [multi-tenancy] TODO
    """

    application_id = models.UUIDField(verbose_name=_("所属应用"), null=False)
    module_id = models.UUIDField(verbose_name=_("所属模块"), null=True)
    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_("挂载资源名"))
    data = models.JSONField(default=dict)
    display_name = models.CharField(max_length=63, null=True, help_text=_("挂载资源展示名称"))

    def get_display_name(self):
        return self.display_name or f"ConfigMap-{self.created.strftime('%y%m%d%H%M')}"

    class Meta:
        unique_together = ("name", "application_id", "environment_name")


class PersistentStorageSource(TimestampedModel):
    """持久存储类型的挂载资源

    [multi-tenancy] TODO
    """

    application_id = models.UUIDField(verbose_name=_("所属应用"), null=False)
    module_id = models.UUIDField(verbose_name=_("所属模块"), null=True)
    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_("挂载资源名"))
    storage_size = models.CharField(max_length=63)
    storage_class_name = models.CharField(max_length=63)
    display_name = models.CharField(max_length=63, null=True, help_text=_("挂载资源展示名称"))

    def get_display_name(self):
        return self.display_name or f"PersistentStorage-{self.created.strftime('%y%m%d%H%M')}"

    class Meta:
        unique_together = ("name", "application_id", "environment_name")


class Mount(TimestampedModel):
    """挂载配置

    [multi-tenancy] TODO
    """

    module_id = models.UUIDField(verbose_name=_("所属模块"), null=False)
    module = ModuleAttrFromID()

    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_("挂载点的名称"))
    mount_path = models.CharField(max_length=128)
    source_type = models.CharField(choices=VolumeSourceType.get_choices(), max_length=32)
    source_config: VolumeSource = SourceConfigField()
    # https://kubernetes.io/docs/concepts/storage/volumes/#using-subpath
    sub_paths = models.JSONField(default=[], help_text="子路径配置")

    @property
    def get_source_name(self):
        if self.source_type == VolumeSourceType.ConfigMap and self.source_config.configMap:
            return self.source_config.configMap.name
        elif self.source_type == VolumeSourceType.PersistentStorage and self.source_config.persistentStorage:
            return self.source_config.persistentStorage.name
        return None

    class Meta:
        unique_together = ("module_id", "mount_path", "environment_name")
