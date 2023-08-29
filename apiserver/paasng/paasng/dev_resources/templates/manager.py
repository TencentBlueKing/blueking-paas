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
from operator import attrgetter
from typing import Dict, List, Optional

from attrs import define
from django.core.exceptions import ObjectDoesNotExist

from paasng.dev_resources.templates.exceptions import TmplRegionNotSupported
from paasng.dev_resources.templates.models import Template
from paasng.engine.constants import RuntimeType
from paasng.platform.modules.constants import APP_CATEGORY
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from paasng.platform.modules.models.deploy_config import ImageTagOptions

logger = logging.getLogger(__name__)


@define
class BuildConfig:
    """BuildConfig dataclass, provide similar attribute of models.BuildConfig"""

    build_method: RuntimeType
    tag_options: ImageTagOptions

    dockerfile_path: Optional[str] = None
    docker_build_args: Optional[Dict] = None

    buildpacks: Optional[List[AppBuildPack]] = None
    buildpack_builder: Optional[AppSlugBuilder] = None
    buildpack_runner: Optional[AppSlugRunner] = None


def retrieve_template_build_config(region: str, template: Template) -> BuildConfig:
    """根据传入的 region 和 template 构造根据该模板创建应用时会使用的 BuildConfig 对象"""
    mgr = TemplateRuntimeManager(region=region, tmpl_name=template.name)
    if template.runtime_type == RuntimeType.DOCKERFILE:
        return mgr.get_docker_build_config()

    try:
        builder = AppSlugBuilder.objects.select_default_runtime(
            region=region, labels={"language": template.language, "category": APP_CATEGORY.NORMAL_APP.value}
        )
        runner = AppSlugRunner.objects.select_default_runtime(
            region=region, labels={"language": template.language, "category": APP_CATEGORY.NORMAL_APP.value}
        )
    except ObjectDoesNotExist:
        logger.warning("default image is not found")
        raise
    return BuildConfig(
        build_method=RuntimeType.BUILDPACK,
        buildpacks=mgr.get_required_buildpacks(bp_stack_name=builder.name),
        buildpack_builder=builder,
        buildpack_runner=runner,
        tag_options=ImageTagOptions(),
    )


class TemplateRuntimeManager:
    """模板的运行时管理器"""

    def __init__(self, region: str, tmpl_name: str):
        self.region = region
        self.template = Template.objects.get(name=tmpl_name)
        if region not in self.template.enabled_regions:
            raise TmplRegionNotSupported

    def get_preset_services_config(self) -> Dict[str, Dict]:
        """获取预设增强服务配置"""
        return self.template.preset_services_config

    def get_docker_build_config(self) -> BuildConfig:
        """获取 Docker 构建配置"""
        # TODO: 在支持 Dockerfile 类型的模板时，重新提供合理的实现
        return BuildConfig(
            build_method=RuntimeType.DOCKERFILE,
            dockerfile_path="Dockerfile",
            docker_build_args={},
            tag_options=ImageTagOptions(),
        )

    def get_required_buildpacks(self, bp_stack_name: str) -> List[AppBuildPack]:
        """获取构建模板代码需要的运行时"""
        try:
            bps_before_language = self.get_template_required_buildpacks(bp_stack_name=bp_stack_name)
        except Template.DoesNotExist:
            bps_before_language = []
        language_bp = self.get_language_buildpack(bp_stack_name=bp_stack_name)
        if language_bp:
            return bps_before_language + [language_bp]
        return bps_before_language

    def get_template_required_buildpacks(self, bp_stack_name: str) -> List[AppBuildPack]:
        """获取模板声明的需要依赖的构建工具"""
        required_buildpacks = self.template.required_buildpacks
        if isinstance(required_buildpacks, list):
            bp_names = required_buildpacks
        elif isinstance(required_buildpacks, dict):
            if stack_required_buildpacks := required_buildpacks.get(bp_stack_name):
                bp_names = stack_required_buildpacks
            else:
                bp_names = required_buildpacks.get("__default__") or []
        else:
            raise ValueError("required_buildpacks is invalid")

        builder = AppSlugBuilder.objects.get(name=bp_stack_name)
        available_bps = {}
        for bp in builder.list_region_available_buildpacks(region=self.region, name__in=bp_names):
            available_bps[bp.name] = bp

        buildpacks = []
        for name in bp_names:
            try:
                buildpacks.append(available_bps[name])
            except KeyError:
                raise RuntimeError('No buildpacks can be found for name: {}'.format(name))

        return buildpacks

    def get_language_buildpack(self, bp_stack_name: str) -> Optional[AppBuildPack]:
        """获取和模块(或模板)语言相关的构建工具"""
        builder = AppSlugBuilder.objects.get(name=bp_stack_name)
        buildpacks = builder.list_region_available_buildpacks(region=self.region, language=self.template.language)
        if not buildpacks:
            return None
        # 选取指定语言的最新一个非隐藏的 buildpack
        buildpack = sorted(buildpacks, key=attrgetter("created"))[-1]
        return buildpack
