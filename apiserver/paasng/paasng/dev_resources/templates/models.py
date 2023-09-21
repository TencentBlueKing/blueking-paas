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
import logging
from typing import List

from django.db import models
from django.utils.translation import gettext_lazy as _
from translated_fields import TranslatedFieldWithFallback

from paasng.dev_resources.templates.constants import TemplateType
from paasng.engine.constants import RuntimeType
from paasng.utils.models import AuditedModel

logger = logging.getLogger(__name__)


class TemplateManager(models.Manager):
    def filter_by_region(self, region: str, type: TemplateType = TemplateType.NORMAL) -> List['Template']:
        """过滤出某个版本支持的模板"""
        return [t for t in self.filter(type=type) if region in t.enabled_regions]


class Template(AuditedModel):
    """开发模板配置"""

    name = models.CharField(verbose_name=_('模板名称'), unique=True, max_length=64)
    type = models.CharField(verbose_name=_('模板类型'), choices=TemplateType.get_django_choices(), max_length=16)
    display_name = TranslatedFieldWithFallback(models.CharField(verbose_name=_('展示用名称'), max_length=64))
    description = TranslatedFieldWithFallback(models.CharField(verbose_name=_('模板描述'), max_length=128))
    language = models.CharField(verbose_name=_('开发语言'), max_length=32)
    market_ready = models.BooleanField(verbose_name=_('能否发布到应用集市'), default=False)
    preset_services_config = models.JSONField(verbose_name=_('预设增强服务配置'), blank=True, default=dict)
    blob_url = models.JSONField(verbose_name=_('不同版本二进制包存储路径'))
    enabled_regions = models.JSONField(verbose_name=_('允许被使用的版本'), blank=True, default=list)
    required_buildpacks = models.JSONField(verbose_name=_('必须的构建工具'), blank=True, default=list)
    processes = models.JSONField(verbose_name=_('进程配置'), blank=True, default=dict)
    tags = models.JSONField(verbose_name=_('标签'), blank=True, default=list)
    repo_url = models.CharField(verbose_name=_('代码仓库信息'), max_length=256, blank=True, default='')
    runtime_type = models.CharField(verbose_name=_("运行时类型"), max_length=32, default=RuntimeType.BUILDPACK)

    objects = TemplateManager()

    class Meta:
        ordering = ['created']
