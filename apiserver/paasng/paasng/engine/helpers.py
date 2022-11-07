# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

from paasng.engine.constants import RuntimeType
from paasng.engine.controller.cluster import Cluster, get_engine_app_cluster
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.specs import ModuleSpecs

if TYPE_CHECKING:
    from paasng.dev_resources.sourcectl.models import VersionInfo
    from paasng.engine.models import EngineApp
    from paasng.platform.applications.models import Application
    from paasng.platform.modules.models.module import Module
    from paasng.platform.modules.models.runtime import AppBuildPack, AppSlugBuilder


@dataclass
class SlugbuilderInfo:
    """表示与模块相关的构建环境信息"""

    module: 'Module'
    slugbuilder: 'AppSlugBuilder'
    buildpacks: List['AppBuildPack']
    environments: Dict

    @property
    def build_image(self) -> Optional[str]:
        """完整 Docker 镜像名"""
        if not self.slugbuilder:
            return None
        return self.slugbuilder.full_image

    @property
    def buildpacks_info(self) -> List[Dict]:
        """完整的 buildpacks JSON 表示方式"""
        if not self.buildpacks:
            return []

        buildpacks = []
        for i in self.buildpacks:
            buildpacks.append(i.info)
        return buildpacks

    @classmethod
    def from_module(cls, module: 'Module') -> 'SlugbuilderInfo':
        """根据模块获取支持的构建环境"""
        from paasng.platform.modules.helpers import ModuleRuntimeManager

        manager = ModuleRuntimeManager(module)
        buildpacks = manager.list_buildpacks()  # buildpack 和 slugbuilder 的约束由配置入口去处理,不再进行检查
        environments = {}
        slugbuilder = manager.get_slug_builder(raise_exception=False)
        if slugbuilder:
            environments.update(slugbuilder.environments)

        buildpacks = buildpacks or []
        for buildpack in buildpacks:
            environments.update(buildpack.environments)

        return cls(module=module, slugbuilder=slugbuilder, buildpacks=buildpacks, environments=environments)

    @classmethod
    def from_engine_app(cls, app: 'EngineApp') -> 'SlugbuilderInfo':
        """根据 engine app 获取支持的构建环境"""
        return cls.from_module(app.env.module)


class RuntimeInfo:
    """解析与 Deployment 相关的运行时环境信息的工具"""

    def __init__(self, engine_app: 'EngineApp', version_info: 'VersionInfo'):
        self.engine_app = engine_app
        self.module = engine_app.env.module
        self.version_info: 'VersionInfo' = version_info
        self.module_spec = ModuleSpecs(self.module)

    @property
    def type(self) -> RuntimeType:
        """返回当前 engine_app 的运行时的类型, buildpack 或者 custom_image"""
        return self.module_spec.runtime_type

    @property
    def image(self) -> Optional[str]:
        """返回当前 engine_app 启动的镜像"""
        if self.type == RuntimeType.CUSTOM_IMAGE:
            repo_url = self.module.get_source_obj().get_repo_url()
            reference = self.version_info.revision
            return f"{repo_url}:{reference}"
        elif self.module.get_source_origin() == SourceOrigin.S_MART and self.version_info.version_type == "image":
            from paasng.extensions.smart_app.utils import SMartImageManager

            named = SMartImageManager(self.module).get_image_info(self.version_info.revision)
            return f"{named.domain}/{named.name}:{named.tag}"

        slugrunner = self.module.slugrunners.last()
        return getattr(slugrunner, "full_image", '')

    @property
    def endpoint(self) -> List:
        """返回当前 engine_app 镜像启动的 endpoint"""
        if self.type == RuntimeType.CUSTOM_IMAGE:
            return ["env"]
        # TODO: 每个 slugrunner 可以配置镜像的 ENTRYPOINT
        slugrunner = self.module.slugrunners.last()
        metadata: Dict = getattr(slugrunner, "metadata", {})
        return metadata.get("endpoint", ['bash', '/runner/init'])


def get_application_cluster(application: 'Application') -> Cluster:
    """Return the cluster name of app's default module"""
    default_module = application.get_default_module()
    engine_app = default_module.envs.get(environment='prod').engine_app
    cluster = get_engine_app_cluster(application.region, engine_app.name)
    return cluster
