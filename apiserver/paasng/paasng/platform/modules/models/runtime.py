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
import operator
from functools import reduce
from typing import TYPE_CHECKING, Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from jsonfield import JSONField
from translated_fields import TranslatedFieldWithFallback

from paasng.platform.modules.constants import AppImageType, BuildPackType
from paasng.utils.models import TimestampedModel

if TYPE_CHECKING:
    from .module import Module

logger = logging.getLogger(__name__)


class BuildpackManager(models.Manager):
    def filter_module_available(self, module: "Module", contain_hidden: bool = False) -> models.QuerySet:
        """查询模块可用的构建工具

        规则: 当前模块下的未隐藏镜像(公共镜像) 或 已被绑定至该模块的镜像(私有镜像)"""
        filters = []

        # 关联已被绑定至该模块的镜像
        try:
            filters.append(models.Q(related_build_configs__pk=module.build_config.pk))
        except ObjectDoesNotExist:
            logger.debug("module %s 未初始化 BuildConfig", module)

        # 给迁移应用绑定镜像时，需要绑定隐藏的构建工具
        if not contain_hidden:
            filters.append(models.Q(is_hidden=False))

        qs = self.get_queryset().filter(reduce(operator.or_, filters))
        # Q: 为什么需要调用 distinct ?
        # A: 因为 models.Q(related_build_configs=module.build_config.pk) 的查询涉及跨越多个表, 因此需要使用 distinct 进行去重
        return qs.distinct()

    def filter_available(self, contain_hidden: bool = False) -> models.QuerySet:
        """查询可用的构建工具"""
        qs = self.get_queryset()
        if not contain_hidden:
            qs = qs.filter(is_hidden=False)
        return qs

    def get_by_natural_key(self, name):
        return self.get(name=name)


class AppBuildPack(TimestampedModel):
    """buildpack 配置

    [multi-tenancy] This model is not tenant-aware.
    """

    language = models.CharField(verbose_name="编程语言", max_length=32)
    type = models.CharField(verbose_name="引用类型", max_length=32, choices=BuildPackType.get_choices())
    name = models.CharField(verbose_name="名称", max_length=64)
    display_name = TranslatedFieldWithFallback(
        models.CharField(verbose_name="展示名称", max_length=64, default="", blank=True)
    )
    address = models.CharField(verbose_name="地址", max_length=2048)
    # 如果是 git 的话需要保证存在对应版本的 tag
    version = models.CharField(verbose_name="版本", max_length=32)
    environments = JSONField(verbose_name="环境变量", default=dict, blank=True)
    # 这个影响用户能否在设置中看见，处理当前版本未就绪/不建议使用/私有定制的情况
    is_hidden = models.BooleanField(verbose_name="是否隐藏", default=False)
    description = TranslatedFieldWithFallback(models.CharField(verbose_name="描述", max_length=1024, blank=True))

    objects = BuildpackManager()

    def natural_key(self):
        return (self.name,)

    @property
    def info(self):
        """controller 支持的 buildpacks JSON 格式"""
        return {
            "type": self.type,
            "name": self.name,
            "url": self.address,
            "version": self.version,
        }

    def __str__(self) -> str:
        return f"{self.name}[{self.pk}]"


class AppImageStackQuerySet(models.QuerySet):
    def filter_module_available(self, module: "Module", contain_hidden: bool = False) -> models.QuerySet:
        """过滤模块可用的镜像

        规则: 当前模块下的未隐藏镜像(公共镜像) 或 已被绑定至该模块的镜像(私有镜像)"""
        filters = []

        # 关联已被绑定至该模块的镜像
        try:
            filters.append(models.Q(buildconfig__pk=module.build_config.pk))
        except ObjectDoesNotExist:
            logger.debug("module %s 未初始化 BuildConfig", module)

        # 给迁移应用绑定镜像时，需要绑定隐藏的镜像
        if not contain_hidden:
            filters.append(models.Q(is_hidden=False))

        qs = self.filter(reduce(operator.or_, filters))
        # Q: 为什么需要调用 distinct ?
        # A: 因为 models.Q(buildconfig__pk=module.build_config.pk) 的查询涉及跨越多个表, 因此需要使用 distinct 进行去重
        return qs.distinct()

    def filter_available(self, contain_hidden: bool = False) -> models.QuerySet:
        """过滤可用的镜像"""
        qs = self.all()
        if not contain_hidden:
            qs = qs.filter(is_hidden=False)
        return qs

    def filter_by_full_image(self, full_image: str) -> models.QuerySet:
        """通过镜像全名过滤"""
        ids = []
        for i in self:
            if i.full_image == full_image:
                ids.append(i.pk)
        if ids:
            return self.filter(id__in=ids)
        return self.none()

    def filter_by_labels(self, labels: Dict[str, str]) -> models.QuerySet:
        """根据label查询可用的镜像

        目前支持:
        - smart_app: 能且只能给（Python + Smart）应用使用
          - label: {'language': 'Python', 'category': 'smart_app'}
        - region-legacy: 给从 PaaS2.0 迁移过来的应用使用
          - label: {'category': 'legacy_app'}
        - other_image: 给上述情况外的其他应用使用
          - label: {}

        :return: available_runtimes
        """
        selected_ids = []
        # 根据 labels 匹配镜像
        for obj in self:
            if set(labels.items()).issubset(obj.labels.items()):
                selected_ids.append(obj.id)
        if selected_ids:
            return self.filter(id__in=selected_ids)
        # 没有匹配到
        return self.none()


class AppImageStackManager(models.Manager):
    _queryset_class = AppImageStackQuerySet

    def filter_module_available(self, module: "Module", contain_hidden: bool = False) -> models.QuerySet:
        """过滤模块可用的镜像

        规则: 当前模块下的未隐藏镜像(公共镜像) 或 已被绑定至该模块的镜像(私有镜像)"""
        return self.get_queryset().filter_module_available(module=module, contain_hidden=contain_hidden)

    def filter_by_full_image(self, module: "Module", full_image: str, contain_hidden: bool = False) -> models.QuerySet:
        """通过镜像全名过滤"""
        return self.filter_module_available(module, contain_hidden=contain_hidden).filter_by_full_image(
            full_image=full_image
        )

    def filter_by_labels(
        self, module: "Module", labels: Dict[str, str], contain_hidden: bool = False
    ) -> models.QuerySet:
        """根据label查询可用的镜像"""
        return self.filter_module_available(module, contain_hidden).filter_by_labels(labels)

    def select_default_runtime(self, labels: dict, contain_hidden: bool = False) -> "AppImage":
        """选择符合对应 labels 的默认运行时

        :raise ObjectDoesNotExist: when no available runtime
        """
        original_qs = self.get_queryset().filter_available(contain_hidden=contain_hidden)  # type: AppImageStackQuerySet

        # firstly, try to select default runtime by labels
        if labels and (available_runtimes := original_qs.filter_by_labels(labels)).exists():
            # return the latest `created` one, but `is_default` has higher priority
            return available_runtimes.latest("is_default", "created")

        # secondly, try to select default runtime by field "is_default"
        if (available_runtimes := original_qs.filter(is_default=True)).exists():
            # return the latest `created` one
            return available_runtimes.latest("created")

        # finally, try to select default runtime by settings
        try:
            return original_qs.get(name=settings.DEFAULT_RUNTIME_IMAGES)
        except self.model.DoesNotExist:
            raise ObjectDoesNotExist

    def get_by_natural_key(self, name):
        return self.get(name=name)


class AppImage(TimestampedModel):
    """应用基础镜像

    [multi-tenancy] This model is not tenant-aware.
    """

    # 代表其基础镜像,如 ceder14 或 heroku18,相同的名称表示运行环境一致
    name = models.CharField(verbose_name="名称", max_length=64, unique=True)
    display_name = TranslatedFieldWithFallback(
        models.CharField(verbose_name="展示名称", max_length=64, default="", blank=True)
    )
    type = models.CharField(verbose_name="镜像类型", max_length=32, choices=AppImageType.get_choices())

    image = models.CharField(verbose_name="镜像", max_length=256)
    tag = models.CharField(verbose_name="标签", max_length=32)
    # 这个影响用户能否在设置中看见，处理当前版本未就绪/不建议使用/私有定制的情况
    is_hidden = models.BooleanField(verbose_name="是否隐藏", default=False)
    is_default = models.BooleanField(null=True, verbose_name="是否为默认运行时", default=False)
    description = TranslatedFieldWithFallback(models.CharField(verbose_name="描述", max_length=1024, blank=True))
    environments = JSONField(verbose_name="环境变量", default=dict, blank=True)
    labels = JSONField(verbose_name="镜像标记", default=dict, blank=True)

    def set_label(self, key: str, value: str):
        """设置标签，默认覆盖原有内容"""
        self.labels[key] = value
        self.save(update_fields=["labels", "updated"])

    def get_label(self, key: str) -> Optional[str]:
        """通过 key 获取 label 内容"""
        return self.labels.get(key)

    @property
    def full_image(self) -> str:
        """Docker 镜像名称"""
        tag = self.tag
        if not tag:
            tag = "latest"
        return ":".join([self.image, tag])

    def __str__(self) -> str:
        return f"{self.name}[{self.pk}]"

    class Meta:
        abstract = True

    def natural_key(self):
        return (self.name,)


class AppSlugRunner(AppImage):
    """应用运行环境

    [multi-tenancy] This model is not tenant-aware.
    """

    objects = AppImageStackManager()


class AppSlugBuilder(AppImage):
    """应用构建环境

    [multi-tenancy] This model is not tenant-aware.
    """

    # 字段指示该环境可用的 buildpacks
    buildpacks = models.ManyToManyField(AppBuildPack, related_name="slugbuilders")
    # 开发沙箱镜像（若为空表示不支持沙箱）
    dev_sandbox_image = models.CharField(verbose_name="开发沙箱镜像（含 Tag）", max_length=256, blank=True)

    step_meta_set = models.ForeignKey(
        "engine.StepMetaSet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="slugbuilders",
        help_text="构建步骤集",
    )

    objects = AppImageStackManager()

    def get_buildpack_choices(self, module: "Module", *args, **kwargs) -> List[AppBuildPack]:
        """查询模块可用的构建工具

        :param args: other filter params
        :param kwargs: other filter params
        """
        return list(self.buildpacks.filter_module_available(module).filter(*args, **kwargs))

    def list_available_buildpacks(self, *args, **kwargs) -> List[AppBuildPack]:
        """查询可用的构建工具"""
        return list(self.buildpacks.filter_available().filter(*args, **kwargs))
