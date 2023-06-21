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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import cattr
from attrs import define
from django.db import models
from django.utils.translation import gettext_lazy as _
from jsonfield import JSONField

from paasng.engine.constants import RuntimeType
from paasng.platform.modules.constants import DeployHookType
from paasng.utils.models import UuidAuditedModel, make_json_field, make_legacy_json_field

if TYPE_CHECKING:
    from paasng.platform.modules.models.module import Module


@define
class Hook:
    type: DeployHookType
    command: str
    enabled: bool = True


class HookList(List[Hook]):
    # warning: 确保 HookList 类型能通过 cattrs 的 is_sequence 判断
    __origin__ = List[Hook]

    def get_hook(self, type_: DeployHookType) -> Optional[Hook]:
        for hook in self:
            if hook.type == type_:
                return hook
        return None

    def upsert(self, type_: DeployHookType, command: str):
        hook = self.get_hook(type_)
        if hook:
            hook.command = command
            hook.enabled = True
        else:
            self.append(Hook(type=type_, command=command))

    def disable(self, type_: DeployHookType):
        hook = self.get_hook(type_)
        if hook:
            hook.enabled = False

    @staticmethod
    def __cattrs_structure__(items, cl):
        return cl(cattr.structure(items, List[Hook]))

    @staticmethod
    def __cattrs_unstructure__(value):
        return cattr.unstructure(list(value))


HookListField = make_legacy_json_field("HookListField", HookList)
cattr.register_structure_hook(HookList, HookList.__cattrs_structure__)
cattr.register_unstructure_hook(HookList, HookList.__cattrs_unstructure__)


# TODO: rename to ReleaseConfig
class DeployConfig(UuidAuditedModel):
    module = models.OneToOneField(
        'modules.Module', on_delete=models.CASCADE, db_constraint=False, related_name="deploy_config"
    )
    procfile = JSONField(default=dict, help_text="部署命令")
    hooks: HookList = HookListField(help_text="部署钩子", default=HookList)


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
    with_commit_id: bool = True


ImageTagOptionsField = make_json_field("ImageTagOptionsField", ImageTagOptions)


class BuildConfigManager(models.Manager):
    def get_or_create_by_module(self, module) -> "BuildConfig":
        obj, _ = self.get_or_create(module=module)
        return obj


class BuildConfig(UuidAuditedModel):
    module = models.OneToOneField(
        'modules.Module', on_delete=models.CASCADE, db_constraint=False, related_name="build_config"
    )
    build_method = models.CharField(verbose_name=_("构建方式"), max_length=32, default=RuntimeType.BUILDPACK)

    # buildpacks 相关配置
    buildpacks = models.ManyToManyField('modules.AppBuildPack', related_name="related_build_configs", null=True)
    buildpack_builder = models.ForeignKey(
        'modules.AppSlugBuilder', on_delete=models.SET_NULL, db_constraint=False, null=True
    )
    buildpack_runner = models.ForeignKey(
        'modules.AppSlugRunner', on_delete=models.SET_NULL, db_constraint=False, null=True
    )

    # docker build 相关配置
    dockerfile_path = models.CharField(
        max_length=512, null=True, help_text=_("Dockerfile文件路径, 必须保证 Dockerfile 在构建目录下, 填写时无需包含构建目录")
    )
    docker_build_args = DockerBuildArgsField(default=dict)

    # Image Tag Policy
    tag_options: ImageTagOptions = ImageTagOptionsField(default=ImageTagOptions)
    objects = BuildConfigManager()

    def update_with_build_method(
        self,
        build_method: RuntimeType,
        module: 'Module',
        bp_stack_name: Union[str, None],
        buildpacks: List[Dict[str, Any]],
        dockerfile_path: Union[str, None],
        docker_build_args: Union[Dict[str, str], None],
    ) -> None:
        """根据指定的 build_method 更新部分字段"""
        from paasng.platform.modules.helpers import ModuleRuntimeBinder

        # 基于 buildpack 的构建方式
        if build_method == RuntimeType.BUILDPACK:
            bp_stack_name = bp_stack_name
            buildpack_ids = [item["id"] for item in buildpacks]

            binder = ModuleRuntimeBinder(module)
            binder.bind_bp_stack(bp_stack_name, buildpack_ids)

            self.build_method = build_method
            self.save(update_fields=["build_method", "updated"])
        # 基于 Dockerfile 的构建方式
        elif build_method == RuntimeType.DOCKERFILE:
            self.build_method = build_method
            self.dockerfile_path = dockerfile_path
            self.docker_build_args = docker_build_args
            self.save(update_fields=["build_method", "dockerfile_path", "docker_build_args", "updated"])
        # 自定义镜像及其他
        else:
            self.build_method = build_method
            self.save(update_fields=["build_method", "updated"])
