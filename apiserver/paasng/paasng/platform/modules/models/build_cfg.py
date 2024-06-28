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

from typing import Dict, Optional

from attr import define
from django.db import models
from django.utils.translation import gettext_lazy as _

from paasng.platform.engine.constants import RuntimeType
from paasng.utils.models import UuidAuditedModel, make_json_field

DockerBuildArgsField = make_json_field("DockerBuildArgsField", Dict[str, str])


@define
class ImageTagOptions:
    """镜像 Tag 选项"""

    prefix: Optional[str] = None
    # 镜像Tag 是否带有分支/标签
    with_version: bool = True
    # 镜像 Tag 是否带有构建时间
    with_build_time: bool = True
    # 镜像 Tag 是否带有提交ID(hash)
    with_commit_id: bool = False


ImageTagOptionsField = make_json_field("ImageTagOptionsField", ImageTagOptions)


class BuildConfigManager(models.Manager):
    def get_or_create_by_module(self, module) -> "BuildConfig":
        obj, _ = self.get_or_create(module=module)
        return obj


class BuildConfig(UuidAuditedModel):
    module = models.OneToOneField(
        "modules.Module", on_delete=models.CASCADE, db_constraint=False, related_name="build_config"
    )
    build_method = models.CharField(verbose_name=_("构建方式"), max_length=32, default=RuntimeType.BUILDPACK)

    # buildpacks 相关配置
    buildpacks = models.ManyToManyField("modules.AppBuildPack", related_name="related_build_configs", null=True)
    buildpack_builder = models.ForeignKey(
        "modules.AppSlugBuilder", on_delete=models.SET_NULL, db_constraint=False, null=True
    )
    buildpack_runner = models.ForeignKey(
        "modules.AppSlugRunner", on_delete=models.SET_NULL, db_constraint=False, null=True
    )

    # docker build 相关配置
    dockerfile_path = models.CharField(
        max_length=512,
        null=True,
        help_text=_("Dockerfile文件路径, 必须保证 Dockerfile 在构建目录下, 填写时无需包含构建目录"),
    )
    docker_build_args = DockerBuildArgsField(default=dict)

    # custom image 相关配置
    # Note: 如需要支持将镜像推送到外部仓库时, 可复用 image_repository 字段
    image_repository = models.TextField(verbose_name=_("镜像仓库"), null=True)
    image_credential_name = models.CharField(verbose_name=_("镜像凭证名称"), null=True, max_length=32)

    # Image Tag Policy
    tag_options: ImageTagOptions = ImageTagOptionsField(default=ImageTagOptions)

    # 高级选项
    use_bk_ci_pipeline = models.BooleanField(help_text="是否使用蓝盾流水线构建", default=False)

    objects = BuildConfigManager()
