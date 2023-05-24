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
import base64
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

from django.conf import settings

from paas_wl.platform.applications.models.build import Build
from paas_wl.release_controller.models import ContainerRuntimeSpec
from paas_wl.resources.kube_res.base import Schedule

if TYPE_CHECKING:
    from paasng.engine.models import EngineApp
    from paasng.platform.modules.models.module import Module
    from paasng.platform.modules.models.runtime import AppBuildPack, AppSlugBuilder


def build_app_registry_auth() -> str:
    auth = f"{settings.APP_DOCKER_REGISTRY_USERNAME}:{settings.APP_DOCKER_REGISTRY_PASSWORD}".encode()
    return "Basic " + base64.b64encode(auth).decode()


@dataclass
class SlugbuilderInfo:
    """表示与模块相关的构建环境信息"""

    module: 'Module'
    slugbuilder: 'AppSlugBuilder'
    buildpacks: List['AppBuildPack']
    # builder + buildpacks 的环境变量
    environments: Dict
    # cnb runtime will build application as Container Image
    use_cnb: bool = False

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
        use_cnb = False
        if slugbuilder:
            environments.update(slugbuilder.environments)
            if manager.is_cnb_runtime:
                use_cnb = True
                environments.update(
                    CNB_REGISTRY_AUTH=json.dumps({settings.APP_DOCKER_REGISTRY_HOST: build_app_registry_auth()})
                )

        buildpacks = buildpacks or []
        for buildpack in buildpacks:
            environments.update(buildpack.environments)

        return cls(
            module=module,
            slugbuilder=slugbuilder,
            buildpacks=buildpacks,
            environments=environments,
            use_cnb=use_cnb,
        )

    @classmethod
    def from_engine_app(cls, app: 'EngineApp') -> 'SlugbuilderInfo':
        """根据 engine app 获取支持的构建环境"""
        return cls.from_module(app.env.module)


def get_processes_by_build(build_id: str) -> Dict[str, str]:
    """Get processes by build id

    :raise: RuntimeError when build not found
    """
    processes = Build.objects.get(pk=build_id).procfile
    if not processes:
        raise RuntimeError("can't find processes in engine")
    return processes


@dataclass
class SlugBuilderTemplate:
    """The Template to run the slug-builder Pod

    :param name: the name of the Pod
    :param namespace: the namespace of the Pod
    :param runtime: Runtime Info of the Pod, including image, pullSecrets, command, args and so on.
    :param schedule: Schedule Rule of the Pod, including tolerations and node_selector.
    """

    name: str
    namespace: str
    runtime: ContainerRuntimeSpec
    schedule: Schedule
