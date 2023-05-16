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
from pathlib import Path
from typing import Dict, Optional

import cattr
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from paas_wl.workloads.processes.models import ProcessTmpl
from paasng.accessories.smart_advisor.models import cleanup_module, tag_module
from paasng.accessories.smart_advisor.tagging import dig_tags_local_repo
from paasng.dev_resources.sourcectl.controllers.package import PackageController
from paasng.dev_resources.sourcectl.exceptions import GetAppYamlError, GetProcfileError
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.dev_resources.sourcectl.repo_controller import get_repo_controller
from paasng.dev_resources.sourcectl.utils import DockerIgnore
from paasng.engine.configurations.source_file import get_metadata_reader
from paasng.engine.exceptions import DeployShouldAbortError
from paasng.engine.models import Deployment, EngineApp
from paasng.engine.utils.output import DeployStream, Style
from paasng.extensions.declarative.handlers import DescriptionHandler, get_desc_handler
from paasng.extensions.declarative.models import DeploymentDescription
from paasng.extensions.smart_app.patcher import SourceCodePatcherWithDBDriver
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.utils.validators import PROC_TYPE_MAX_LENGTH, PROC_TYPE_PATTERN

logger = logging.getLogger(__name__)
TypeProcesses = Dict[str, ProcessTmpl]


def validate_processes(processes: Dict[str, Dict[str, str]]) -> TypeProcesses:
    """Validate proc type format

    :param processes:
    :return: validated processes, which all key is lower case.
    :raise: django.core.exceptions.ValidationError
    """
    for proc_type in processes.keys():
        if not PROC_TYPE_PATTERN.match(proc_type):
            raise ValidationError(f'Invalid proc type: {proc_type}, must match pattern {PROC_TYPE_PATTERN.pattern}')
        if len(proc_type) > PROC_TYPE_MAX_LENGTH:
            raise ValidationError(
                f'Invalid proc type: {proc_type}, must not longer than {PROC_TYPE_MAX_LENGTH} characters'
            )

    # Formalize processes data and return
    try:
        return cattr.structure(
            {name.lower(): {"name": name.lower(), **v} for name, v in processes.items()}, TypeProcesses
        )
    except KeyError as e:
        raise ValidationError(f'Invalid process data, missing: {e}')
    except ValueError as e:
        raise ValidationError(f"Invalid process data, {e}")


def get_dockerignore(deployment: Deployment) -> Optional[DockerIgnore]:
    """Get the DockerIgnore from SourceCode"""
    module: Module = deployment.app_environment.module
    operator = deployment.operator
    version_info = deployment.version_info
    relative_source_dir = deployment.get_source_dir()

    try:
        metadata_reader = get_metadata_reader(module, operator=operator, source_dir=relative_source_dir)
        content = metadata_reader.get_dockerignore(version_info)
    except GetProcfileError:
        # 源码中无 dockerignore 文件, 忽略异常
        return None
    except NotImplementedError:
        # 对于不支持从源码读取 .dockerignore 的应用, 忽略异常
        return None
    return DockerIgnore(content)


def get_processes(deployment: Deployment, stream: Optional[DeployStream] = None) -> TypeProcesses:  # noqa: C901
    """Get the ProcessTmpl from SourceCode
    Declarative Processes is a dict containing a process type and its corresponding DeclarativeProcess

    1. Try to get processes data from DeploymentDescription at first.
    2. Try to get the process data from DeployConfig, which only work from Image Application
    3. Try to get the process data from Procfile

    if step (1) and step (3) get processes data both, will use the one got from step (3)

    :param Deployment deployment: 当前的部署对象
    :param DeployStream stream: 日志流对象, 用于记录日志
    :raises: DeployShouldAbortError
    """
    module: Module = deployment.app_environment.module
    operator = deployment.operator
    version_info = deployment.version_info
    relative_source_dir = deployment.get_source_dir()

    proc_data: Optional[Dict[str, Dict[str, str]]] = None
    if deployment:
        try:
            deploy_desc: DeploymentDescription = DeploymentDescription.objects.get(deployment=deployment)
            proc_data = deploy_desc.get_processes()
        except DeploymentDescription.DoesNotExist:
            logger.info("Can't get related DeploymentDescription, read Procfile directly.")

    if not proc_data:
        deploy_config = module.get_deploy_config()
        if deploy_config.procfile:
            proc_data = {name: {"command": command} for name, command in deploy_config.procfile.items()}

    try:
        metadata_reader = get_metadata_reader(module, operator=operator, source_dir=relative_source_dir)
        proc_data_form_source = {
            name: {"command": command} for name, command in metadata_reader.get_procfile(version_info).items()
        }
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
    try:
        return validate_processes(processes=proc_data)
    except ValidationError as e:
        raise DeployShouldAbortError(e.message) from e


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


_current_path = Path('.')


def get_app_description_handler(
    module: Module, operator: str, version_info: VersionInfo, source_dir: Path = _current_path
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


def get_source_package_path(deployment: Deployment) -> str:
    """Return the blobstore path for storing source files package"""
    engine_app = deployment.get_engine_app()
    branch = deployment.source_version_name
    revision = deployment.source_revision

    slug_name = f'{engine_app.name}:{branch}:{revision}'
    return f'{engine_app.region}/home/{slug_name}/tar'


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


def tag_module_from_source_files(module, source_files_path):
    """Dig and tag the module from application source files"""
    try:
        tags = dig_tags_local_repo(str(source_files_path))
        cleanup_module(module)

        logging.info(f"Tagging module[{module.pk}]: {tags}")
        tag_module(module, tags, source="source_analyze")
    except Exception:
        logger.exception("Unable to tagging module")
