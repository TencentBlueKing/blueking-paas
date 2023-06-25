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

from paas_wl.platform.applications.models import Build
from paasng.dev_resources.sourcectl.models import RepoBasicAuthHolder
from paasng.engine.constants import RuntimeType
from paasng.engine.models import Deployment
from paasng.extensions.smart_app.conf import bksmart_settings
from paasng.extensions.smart_app.utils import SMartImageManager
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.models import BuildConfig, Module
from paasng.platform.modules.specs import ModuleSpecs

if TYPE_CHECKING:
    from paasng.dev_resources.sourcectl.models import VersionInfo
    from paasng.engine.models import EngineApp


def generate_image_repository(module: Module) -> str:
    """Get the image repository for storing container image"""
    application = module.application
    system_prefix = f"{settings.APP_DOCKER_REGISTRY_HOST}/{settings.APP_DOCKER_REGISTRY_NAMESPACE}"
    app_part = f"{application.code}/{module.name}"
    return f"{system_prefix}/{app_part}"


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
        self.module = engine_app.env.module
        self.application = self.module.application
        self.module_spec = ModuleSpecs(self.module)

    @property
    def type(self) -> RuntimeType:
        """返回当前 engine_app 的运行时的类型, buildpack 或者 custom_image"""
        return self.module_spec.runtime_type

    def generate_image(self, version_info: 'VersionInfo') -> str:
        """generate the runtime image of the application at a given version"""
        if self.type == RuntimeType.CUSTOM_IMAGE:
            if self.application.type == ApplicationType.CLOUD_NATIVE:
                # 仅托管镜像类型的云原生应用的镜像由 Yaml 定义, 因此返回空字符串
                # Q: 为什么不尝试从 Yaml 解析？
                # A: 因为 v1alpha1 版本的云原生应用并不能保证只有一个 image...
                #    从 Yaml 解析在兼容 v1alpha1 需要写很复杂或依赖约定(例如用 web 的 image)的逻辑, 这反而更难维护。
                return ""
            repo_url = self.module.get_source_obj().get_repo_url()
            reference = version_info.revision
            return f"{repo_url}:{reference}"
        elif self.type == RuntimeType.DOCKERFILE:
            app_image_repository = generate_image_repository(self.module)
            app_image_tag = generate_image_tag(module=self.module, version=version_info)
            return f"{app_image_repository}:{app_image_tag}"
        elif self.module.get_source_origin() == SourceOrigin.S_MART and version_info.version_type == "image":
            from paasng.extensions.smart_app.utils import SMartImageManager

            named = SMartImageManager(self.module).get_image_info(version_info.revision)
            return f"{named.domain}/{named.name}:{named.tag}"
        mgr = ModuleRuntimeManager(self.module)
        slug_runner = mgr.get_slug_runner(raise_exception=False)
        if mgr.is_cnb_runtime:
            return (
                generate_image_repository(self.module)
                + ":"
                + generate_image_tag(module=self.module, version=version_info)
            )
        return getattr(slug_runner, "full_image", '')

    @property
    def entrypoint(self) -> List:
        """返回当前 engine_app 镜像启动的 entrypoint"""
        if self.type == RuntimeType.CUSTOM_IMAGE or self.type == RuntimeType.DOCKERFILE:
            # Note: 关于为什么要使用 env 命令作为 entrypoint, 而不是直接将用户的命令作为 entrypoint.
            # 虽然实际上绝大部分 CRI 实现会在当 Command 非空时 忽略镜像的 CMD(即认为 ENTRYPOINT 和 CMD 是绑定的, 只要 ENTRYPOINT 被修改, 就会忽略 CMD)
            # 但是, 根据 k8s 的文档, 如果 Command/Args 是空值，就会使用镜像的 ENTRYPOINT 和 CMD.
            # 而 Heroku 风格的 Procfile 不是以 entrypoint/cmd 这样的格式描述, 如果只将 procfile 作为 Container 的 Command/Args 都会有潜在风险.
            # 风险点在于: Command/Args 为空时, 有可能会使用镜像的 ENTRYPOINT 和 CMD.
            # ref: https://github.com/containerd/containerd/blob/main/pkg/cri/opts/spec_opts.go#L63
            return ["env"]
        # TODO: 每个 slugrunner 可以配置镜像的 ENTRYPOINT
        mgr = ModuleRuntimeManager(self.module)
        if mgr.is_cnb_runtime:
            return ["launcher"]
        slug_runner = mgr.get_slug_runner(raise_exception=False)
        metadata: Dict = getattr(slug_runner, "metadata", {})
        return metadata.get("entrypoint", ['bash', '/runner/init'])


def update_image_runtime_config(deployment: Deployment):
    """Update the image runtime config of the given engine app"""
    # TODO: runtime 信息应该与 Build 关联(如果需要支持 cnb <-> docker build 互相切换)
    engine_app = deployment.get_engine_app()
    build_obj = Build.objects.get(pk=deployment.build_id)
    image_pull_policy = deployment.advanced_options.image_pull_policy
    runtime = RuntimeImageInfo(engine_app=engine_app)
    runtime_dict = {
        "image": build_obj.image,
        "type": runtime.type,
        "entrypoint": runtime.entrypoint,
        "image_pull_policy": image_pull_policy,
    }

    # Update the config property of WlApp object
    wl_app = engine_app.to_wl_obj()
    config = wl_app.latest_config
    config.runtime = runtime_dict
    config.save(update_fields=['runtime', 'updated'])

    # Refresh resource requirements
    config.refresh_res_reqs()
