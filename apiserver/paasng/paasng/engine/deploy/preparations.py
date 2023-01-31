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
"""Preparation works before doing a application deploy
"""
import logging
from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from paasng.accessories.smart_advisor.models import cleanup_module, tag_module
from paasng.accessories.smart_advisor.tagging import dig_tags_local_repo
from paasng.dev_resources.sourcectl.controllers.package import PackageController
from paasng.dev_resources.sourcectl.exceptions import GetAppYamlError, GetProcfileError
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.dev_resources.sourcectl.repo_controller import get_repo_controller
from paasng.dev_resources.sourcectl.version_services import get_version_service
from paasng.engine.constants import ImagePullPolicy, OperationTypes
from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.deploy.exceptions import DeployShouldAbortError
from paasng.engine.deploy.infras import DeployStream, Style
from paasng.engine.deploy.metadata import get_metadata_reader
from paasng.engine.helpers import RuntimeInfo
from paasng.engine.models import Deployment, EngineApp
from paasng.engine.models.operations import ModuleEnvironmentOperations
from paasng.extensions.declarative.handlers import DescriptionHandler, get_desc_handler
from paasng.extensions.declarative.models import DeploymentDescription
from paasng.extensions.smart_app.patcher import SourceCodePatcherWithDBDriver
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.utils.validators import validate_procfile as _validate_procfile

logger = logging.getLogger(__name__)


# Preparations for build start
def validate_procfile(proc_data: Dict[str, str]) -> Dict[str, str]:
    try:
        return _validate_procfile(procfile=proc_data)
    except ValidationError as e:
        raise DeployShouldAbortError(e.message) from e


def get_processes(deployment: Deployment, stream: Optional[DeployStream] = None) -> Dict[str, str]:
    """Get the processes data from SourceCode
    1. Try to get processes data from DeploymentDescription at first.
    2. Try to get the process data from DeployConfig, which only work from Image Application
    3. Try to get the process data from Procfile

    if step (1) and step (3) get processes data both, will use the one got from step (3)

    :param Deployment deployment: 当前的部署对象
    :param DeployStream stream: 日志流对象, 用于记录日志
    :raises: DeployShouldAbortError
    """
    module = deployment.app_environment.module
    operator = deployment.operator
    version_info = deployment.version_info
    relative_source_dir = deployment.get_source_dir()

    proc_data = None
    if deployment:
        try:
            deploy_desc = DeploymentDescription.objects.get(deployment=deployment)
            proc_data = deploy_desc.get_procfile()
        except DeploymentDescription.DoesNotExist:
            logger.info("Can't get related DeploymentDescription, read Procfile directly.")

    if not proc_data:
        deploy_config = module.get_deploy_config()
        proc_data = deploy_config.procfile

    try:
        metadata_reader = get_metadata_reader(module, operator=operator, source_dir=relative_source_dir)
        proc_data_form_source = metadata_reader.get_procfile(version_info)
    except GetProcfileError as e:
        if not proc_data:
            raise DeployShouldAbortError(reason=f'Procfile error: {e.message}') from e
    except NotImplementedError:
        """对于不支持从源码读取进程信息的应用, 忽略异常, 因为可能在其他分支已成功获取到 proc_data"""
    else:
        if proc_data:
            logger.warning("Process definition conflict, will use the one defined in `Procfile`")
            if stream:
                stream.write_message(
                    Style.Warning(_("Warning: Process definition conflict, will use the one defined in `Procfile`"))
                )
        proc_data = proc_data_form_source

    if proc_data is None:
        raise DeployShouldAbortError(_("Missing process definition"))
    return validate_procfile(proc_data)


def get_app_description_handler(
    module: Module, operator: str, version_info: VersionInfo, source_dir: Path = Path(".")
) -> Optional[DescriptionHandler]:
    """Get App Description handler from app.yaml/app_desc.yaml"""
    try:
        metadata_reader = get_metadata_reader(module, operator=operator, source_dir=source_dir)
    except NotImplementedError:
        return None
    try:
        app_desc = metadata_reader.get_app_desc(version_info)
    except GetAppYamlError:
        return None

    return get_desc_handler(app_desc)


def get_source_dir(module: Module, operator: str, version_info: VersionInfo) -> str:
    """A helper to get source_dir.
    For package App, we should parse source_dir from Application Description File.
    Otherwise,  we must get source_dir from property of module.
    """
    # Note: 对于非源码包类型的应用, 只有产品上配置的部署目录会生效
    if not ModuleSpecs(module).deploy_via_package:
        return module.get_source_obj().get_source_dir()

    # Note: 对于源码包类型的应用, 部署目录需要从源码包根目录下的 app_desc.yaml 中读取
    handler = get_app_description_handler(module, operator, version_info)
    if handler is None:
        return ''
    return handler.get_deploy_desc(module.name).source_dir


def get_source_package_path(deployment: Deployment) -> str:
    """Return the blobstore path for storing source files package"""
    engine_app = deployment.get_engine_app()
    branch = deployment.source_version_name
    revision = deployment.source_revision

    slug_name = f'{engine_app.name}:{branch}:{revision}'
    return f'{engine_app.region}/home/{slug_name}/tar'


def tag_module_from_source_files(module, source_files_path):
    """Dig and tag the module from application source files"""
    try:
        tags = dig_tags_local_repo(str(source_files_path))
        cleanup_module(module)

        logging.info(f"Tagging module[{module.pk}]: {tags}")
        tag_module(module, tags, source="source_analyze")
    except Exception:
        logger.exception("Unable to tagging module")


def download_source_to_dir(module: Module, operator: str, deployment: Deployment, working_path: Path):
    """Download and extract the module's source files to local path, will generate Procfile if necessary

    :param operator: current operator's user_id
    """
    spec = ModuleSpecs(module)
    if spec.source_origin_specs.source_origin in [SourceOrigin.AUTHORIZED_VCS, SourceOrigin.SCENE]:
        get_repo_controller(module, operator=operator).export(working_path, deployment.version_info)
    elif spec.deploy_via_package:
        PackageController.init_by_module(module, operator).export(working_path, deployment.version_info)
    else:
        raise NotImplementedError

    try:
        SourceCodePatcherWithDBDriver(module, working_path, deployment).add_procfile()
    except Exception:
        logger.exception("Unexpected exception occurred when injecting Procfile.")
        return


def check_source_package(engine_app: EngineApp, package_path: Path, stream: DeployStream):
    """Check module source package, produce warning infos"""
    # Check source package size
    warning_threshold = settings.ENGINE_APP_SOURCE_SIZE_WARNING_THRESHOLD_MB
    size = package_path.stat().st_size
    if size > warning_threshold * 1024 * 1024:
        stream.write_message(
            Style.Warning(
                _("WARNING: 应用源码包体积过大（>{warning_threshold}MB），将严重影响部署性能，请尝试清理不必要的文件来减小体积。").format(
                    warning_threshold=warning_threshold
                )
            )
        )
        logger.error(f"Engine app {engine_app.name}'s source is too big, size={size}")


def initialize_deployment(
    env: 'ModuleEnvironment', operator: str, version_info: VersionInfo, advanced_options: Optional[Dict] = None
) -> Deployment:
    """初始化 Deployment 对象, 并记录该次部署事件.

    :param env: 需要部署的模块
    :param operator: 当前 operator 的 user id
    :param version_info: 需要部署的源码版本信息
    :param advanced_options: AdvancedOptionsField, 部署的高级选项.
    """
    module = env.module
    version_service = get_version_service(module, operator=operator)
    source_location = version_service.build_url(version_info)

    deploy_config = module.get_deploy_config()
    deployment = Deployment.objects.create(
        region=module.region,
        operator=operator,
        app_environment=env,
        source_type=module.source_type,
        source_location=source_location,
        source_revision=version_info.revision,
        source_version_type=version_info.version_type,
        source_version_name=version_info.version_name,
        advanced_options=dict(
            **(advanced_options or {}),
            source_dir=get_source_dir(module, operator=operator, version_info=version_info),
        ),
        hooks=deepcopy(deploy_config.hooks),
    )
    ModuleEnvironmentOperations.objects.create(
        operator=deployment.operator,
        app_environment=deployment.app_environment,
        application=deployment.app_environment.application,
        operation_type=OperationTypes.ONLINE.value,
        object_uid=deployment.pk,
    )
    return deployment


# Preparations for release start


def get_processes_by_build(engine_app: EngineApp, build_id: str) -> Dict[str, str]:
    engine_client = EngineDeployClient(engine_app)
    build = engine_client.get_build(build_id)
    processes = build.get("procfile")
    if not processes:
        raise RuntimeError("can't find processes in engine")
    return processes


def update_engine_app_config(
    engine_app: EngineApp,
    version_info: VersionInfo,
    image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT,
):
    """Update engine app's configs by calling remote service"""
    runtime = RuntimeInfo(engine_app=engine_app, version_info=version_info)
    client = EngineDeployClient(engine_app)
    return client.update_config(
        runtime={
            "image": runtime.image,
            "type": runtime.type,
            "endpoint": runtime.endpoint,
            "image_pull_policy": image_pull_policy.value,
        },
    )
