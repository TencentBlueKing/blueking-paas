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
from typing import Union

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from paas_wl.cnative.specs.constants import MountEnvName, VolumeSourceType
from paas_wl.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.platform.applications.relationship import ModuleAttrFromID
from paas_wl.utils.models import TimestampedModel
from paasng.utils.models import make_json_field

SourceConfigField = make_json_field('SourceConfigField', VolumeSource)


class ConfigMapSourceQuerySet(models.QuerySet):
    def get_by_mount(self, m: 'Mount'):
        if m.source_config.configMap:
            return self.get(
                module_id=m.module_id, environment_name=m.environment_name, name=m.source_config.configMap.name
            )
        raise ValueError(f'Mount {m.name} is invalid: source_config.configMap is none')


class ConfigMapSource(TimestampedModel):
    module_id = models.UUIDField(verbose_name=_('所属模块'), null=False)
    module = ModuleAttrFromID()

    environment_name = models.CharField(
        verbose_name=_('环境名称'), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_('ConfigMap 名'))
    data = models.JSONField(default=dict)

    objects = ConfigMapSourceQuerySet.as_manager()

    class Meta:
        unique_together = ('module_id', 'name', 'environment_name')


class Mount(TimestampedModel):
    """挂载配置"""

    module_id = models.UUIDField(verbose_name=_('所属模块'), null=False)
    module = ModuleAttrFromID()

    environment_name = models.CharField(
        verbose_name=_('环境名称'), choices=MountEnvName.get_choices(), null=False, max_length=16
    )
    name = models.CharField(max_length=63, help_text=_('挂载点的名称'))
    mount_path = models.CharField(max_length=128)
    source_type = models.CharField(choices=VolumeSourceType.get_choices(), max_length=32)
    source_config: VolumeSource = SourceConfigField()

    class Meta:
        unique_together = ('module_id', 'mount_path', 'environment_name')

    @cached_property
    def source(self) -> Union[ConfigMapSource]:
        if self.source_type == VolumeSourceType.ConfigMap:
            return ConfigMapSource.objects.get_by_mount(self)
        raise ValueError(f'unsupported source type {self.source_type}')
