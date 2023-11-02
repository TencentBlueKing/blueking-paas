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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

import arrow
from django.conf import settings

from paas_wl.bk_app.applications.models import Build
from paas_wl.bk_app.processes.services import refresh_res_reqs
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.models import Deployment
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.models import BuildConfig, Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.smart_app.conf import bksmart_settings
from paasng.platform.smart_app.utils import SMartImageManager
from paasng.platform.sourcectl.models import RepoBasicAuthHolder

if TYPE_CHECKING:
    from paasng.platform.engine.models import EngineApp
    from paasng.platform.sourcectl.models import VersionInfo


def get_image_repository_template() -> str:
    """Get the image repository template"""
    system_prefix = f"{settings.APP_DOCKER_REGISTRY_HOST}/{settings.APP_DOCKER_REGISTRY_NAMESPACE}"
    return f"{system_prefix}/{{app_code}}/{{module_name}}"


def generate_image_repository(module: Module) -> str:
    """Get the image repository for storing container image"""
    application = module.application
    return get_image_repository_template().format(app_code=application.code, module_name=module.name)


def generate_image_tag(module: Module, version: "VersionInfo") -> str:
    """Get the Image Tag for version"""
    cfg = BuildConfig.objects.get_or_create_by_module(module)
    options = cfg.tag_options
    parts: List[str] = []
    if options.prefix:
        parts.append(options.prefix)
    if options.with_version:
        parts.append(version.version_name)
    if options.with_build_time:
        parts.append(arrow.now().format("YYMMDDHHmm"))
    if options.with_commit_id:
        parts.append(version.revision)
    return "-".join(parts)


@dataclass
class ImageCredential:
    registry: str
    username: str
    password: str


class ImageCredentialManager:
    """A Helper provide the image pull secret for the given Module"""

    def __init__(self, module: Module):
        self.module = module

    def provide(self) -> Optional[ImageCredential]:
        if ModuleSpecs(self.module).deploy_via_package:
            named = SMartImageManager(self.module).get_image_info()
            return ImageCredential(
                registry=f"{named.domain}/{named.name}",
                username=bksmart_settings.registry.username,
                password=bksmart_settings.registry.password,
            )
        source_obj = self.module.get_source_obj()
        repo_full_url = source_obj.get_repo_url()
        try:
            holder = RepoBasicAuthHolder.objects.get_by_repo(module=self.module, repo_obj=source_obj)
            username, password = holder.basic_auth
        except RepoBasicAuthHolder.DoesNotExist:
            username = password = None

        if repo_full_url and username and password:
            return ImageCredential(registry=repo_full_url, username=username, password=password)
        return None


class RuntimeImageInfo:
    """提供与当前应用匹配的运行时环境信息的工具"""

    def __init__(self, engine_app: 'EngineApp'):
        self.engine_app = engine_app
        self.module: Module = engine_app.env.module
        self.application = self.module.application
        self.module_spec = ModuleSpecs(self.module)

    @property
    def type(self) -> RuntimeType:
        """返回当前 engine_app 的运行时的类型, buildpack 或者 custom_image"""
        return self.module_spec.runtime_type

    def generate_image(self, version_info: 'VersionInfo', special_tag: Optional[str] = None) -> str:
        """generate the runtime image of the application at a given version

        :param version_info: 版本信息
        :param special_tag: 指定镜像 Tag
        :return: 返回运行构建产物(Build)的镜像
                 如果构建产物是 Image, 则返回的是镜像
                 如果构建产物是 Slug, 则返回 SlugRunner 的镜像
        """
        if self.type == RuntimeType.CUSTOM_IMAGE:
            if self.application.type == ApplicationType.CLOUD_NATIVE:
                image_tag = special_tag or version_info.version_name
                repository = self.module.build_config.image_repository
                if not repository:
                    # v1alpha1 版本的云原生应用未存储 image_repository 字段
                    # 此处返回空字符串表示不覆盖 manifest 的 image 信息
                    return ""
                return f"{repository}:{image_tag}"
            repo_url = self.module.get_source_obj().get_repo_url()
            reference = version_info.revision
            return f"{repo_url}:{reference}"
        elif self.type == RuntimeType.DOCKERFILE:
            app_image_repository = generate_image_repository(self.module)
            app_image_tag = special_tag or generate_image_tag(module=self.module, version=version_info)
            return f"{app_image_repository}:{app_image_tag}"
        elif self.module.get_source_origin() == SourceOrigin.S_MART and version_info.version_type == "image":
            from paasng.platform.smart_app.utils import SMartImageManager

            named = SMartImageManager(self.module).get_image_info(version_info.revision)
            return f"{named.domain}/{named.name}:{named.tag}"
        mgr = ModuleRuntimeManager(self.module)
        slug_runner = mgr.get_slug_runner(raise_exception=False)
        if mgr.is_cnb_runtime:
            app_image_repository = generate_image_repository(self.module)
            app_image_tag = special_tag or generate_image_tag(module=self.module, version=version_info)
            return f"{app_image_repository}:{app_image_tag}"
        return getattr(slug_runner, "full_image", '')


def update_image_runtime_config(deployment: Deployment):
    """Update the image runtime config of the given engine app"""
    engine_app = deployment.get_engine_app()
    build_obj = Build.objects.get(pk=deployment.build_id)
    image_pull_policy = deployment.advanced_options.image_pull_policy
    runtime = RuntimeImageInfo(engine_app=engine_app)
    runtime_dict = {
        "type": runtime.type,
        "image_pull_policy": image_pull_policy,
    }
    # TODO: 每个 slugrunner 可以配置镜像的 ENTRYPOINT
    mgr = ModuleRuntimeManager(deployment.app_environment.module)
    slug_runner = mgr.get_slug_runner(raise_exception=False)
    metadata: Dict = getattr(slug_runner, "metadata", {})
    if entrypoint := metadata.get("entrypoint"):
        build_obj.artifact_metadata.update(entrypoint=entrypoint)
        build_obj.save(update_fields=["artifact_metadata", "updated"])

    # Update the config property of WlApp object
    wl_app = engine_app.to_wl_obj()
    config = wl_app.latest_config
    config.runtime = runtime_dict
    config.save(update_fields=['runtime', 'updated'])
    # Refresh resource requirements
    refresh_res_reqs(config)
