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
import logging
from pathlib import Path

from django.db import models
from django.utils.translation import gettext_lazy as _
from translated_fields import TranslatedFieldWithFallback

from paasng.platform.engine.constants import RuntimeType
from paasng.platform.templates.constants import TemplateType
from paasng.utils.models import AuditedModel

logger = logging.getLogger(__name__)


class Template(AuditedModel):
    """开发模板配置

    [multi-tenancy] This model is not tenant-aware.
    """

    name = models.CharField(verbose_name=_("模板名称"), unique=True, max_length=64)
    type = models.CharField(verbose_name=_("模板类型"), choices=TemplateType.get_django_choices(), max_length=16)
    display_name = TranslatedFieldWithFallback(models.CharField(verbose_name=_("展示用名称"), max_length=64))
    description = TranslatedFieldWithFallback(models.CharField(verbose_name=_("模板描述"), max_length=128))
    language = models.CharField(verbose_name=_("开发语言"), max_length=32)
    market_ready = models.BooleanField(verbose_name=_("能否发布到应用集市"), default=False)
    preset_services_config = models.JSONField(verbose_name=_("预设增强服务配置"), blank=True, default=dict)

    # NOTE: blob_url 使用了 JSONField 而不是 TextField，是因为 blob_url 曾经是一个包含不同 region 的
    # 包地址的字典对象，在删除了按 region 区分的逻辑后，它的值变为了普通字符串，但继续沿用原来的字段类型。
    blob_url = models.JSONField(verbose_name=_("二进制包存储路径"))

    required_buildpacks = models.JSONField(verbose_name=_("必须的构建工具"), blank=True, default=list)
    processes = models.JSONField(verbose_name=_("进程配置"), blank=True, default=dict)
    tags = models.JSONField(verbose_name=_("标签"), blank=True, default=list)

    repo_type = models.CharField(
        verbose_name=_("代码仓库类型"), max_length=32, default="", help_text="将模板从代码仓库下载到本地时需要使用到"
    )
    repo_url = models.CharField(verbose_name=_("代码仓库地址"), max_length=256, blank=True, default="")
    source_dir = models.CharField(verbose_name=_("模板代码所在目录"), max_length=256, blank=True, default="./")
    # 模板代码渲染方式，可选值：django_template / cookiecutter
    render_method = models.CharField(verbose_name=_("模板渲染方式"), max_length=32, default="django_template")
    runtime_type = models.CharField(verbose_name=_("运行时类型"), max_length=32, default=RuntimeType.BUILDPACK)
    is_hidden = models.BooleanField(
        verbose_name=_("是否隐藏"), help_text=_("被隐藏的模板不会出现在创建应用时的列表中"), default=False
    )

    class Meta:
        ordering = ["created"]

    def get_source_dir(self) -> Path:
        """获取模板代码的相对目录路径

        示例：
        当 source_dir 存储为 "/app/src" 时 -> 返回 "app/src"
        当 source_dir 存储为 "./backend" 时 -> 返回 "backend"
        """
        source_dir = Path(self.source_dir)
        if source_dir.is_absolute():
            return source_dir.relative_to("/")
        return source_dir
