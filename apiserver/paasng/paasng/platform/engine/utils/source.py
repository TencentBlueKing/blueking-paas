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
from pathlib import Path
from typing import Dict, Optional

import cattr
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from paasng.accessories.smart_advisor.models import cleanup_module, tag_module
from paasng.accessories.smart_advisor.tagging import dig_tags_local_repo
from paasng.platform.applications.constants import AppFeatureFlag, ApplicationType
from paasng.platform.applications.models import Application
from paasng.platform.declarative.handlers import DeployDescHandler, get_deploy_desc_by_module, get_deploy_desc_handler
from paasng.platform.engine.configurations.building import get_dockerfile_path
from paasng.platform.engine.configurations.source_file import get_metadata_reader
from paasng.platform.engine.exceptions import InitDeployDescHandlerError, SkipPatchCode
from paasng.platform.engine.models import Deployment, EngineApp
from paasng.platform.engine.models.deployment import ProcessTmpl
from paasng.platform.engine.utils.output import DeployStream, Style
from paasng.platform.engine.utils.patcher import SourceCodePatcherWithDBDriver
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.sourcectl.controllers.package import PackageController
from paasng.platform.sourcectl.exceptions import (
    GetAppYamlError,
    GetAppYamlFormatError,
    GetDockerIgnoreError,
    GetProcfileError,
    GetProcfileFormatError,
)
from paasng.platform.sourcectl.models import VersionInfo
from paasng.platform.sourcectl.repo_controller import get_repo_controller
from paasng.platform.sourcectl.utils import DockerIgnore
from paasng.utils.validators import PROC_TYPE_MAX_LENGTH, PROC_TYPE_PATTERN

logger = logging.getLogger(__name__)
TypeProcesses = Dict[str, ProcessTmpl]


def validate_processes(processes: Dict[str, Dict[str, str]]) -> TypeProcesses:
    """Validate proc type format

    :param processes:
    :return: validated processes, which all key is lower case.
    :raise: django.core.exceptions.ValidationError
    """

    if len(processes) > settings.MAX_PROCESSES_PER_MODULE:
        raise ValidationError(
            f"The number of processes exceeded: maximum {settings.MAX_PROCESSES_PER_MODULE} processes per module, "
            f"but got {len(processes)}"
        )

    for proc_type in processes:
        if not PROC_TYPE_PATTERN.match(proc_type):
            raise ValidationError(f"Invalid proc type: {proc_type}, must match pattern {PROC_TYPE_PATTERN.pattern}")
        if len(proc_type) > PROC_TYPE_MAX_LENGTH:
            raise ValidationError(
                f"Invalid proc type: {proc_type}, must not longer than {PROC_TYPE_MAX_LENGTH} characters"
            )

    # Formalize processes data and return
    try:
        return cattr.structure(
            {name.lower(): {"name": name.lower(), **v} for name, v in processes.items()}, TypeProcesses
        )
    except KeyError as e:
        raise ValidationError(f"Invalid process data, missing: {e}")
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
    except GetDockerIgnoreError:
        # 源码中无 dockerignore 文件, 忽略异常
        return None
    except NotImplementedError:
        # 对于不支持从源码读取 .dockerignore 的应用, 忽略异常
        return None

    # should not ignore dockerfile for kaniko builder
    dockerfile_path = get_dockerfile_path(module)
    return DockerIgnore(content, whitelist=[dockerfile_path])


def get_source_dir(module: Module, operator: str, version_info: VersionInfo) -> str:
    """A helper to get source_dir.
    For package App, we should parse source_dir from Application Description File.
    Otherwise,  we must get source_dir from property of module.
    """
    # NOTE: 对于非源码包类型的应用, 只有产品上配置的部署目录会生效
    if not ModuleSpecs(module).deploy_via_package:
        if source_obj := module.get_source_obj():
            return source_obj.get_source_dir()
        # 模块未绑定 source_obj, 可能是仅托管镜像的云原生应用
        return ""

    # NOTE: 对于源码包类型的应用, 部署目录需要从源码包根目录下的 app_desc.yaml 中读取
    desc_data = get_desc_data_by_version(module, operator, version_info)
    if not desc_data:
        return ""
    return get_deploy_desc_by_module(desc_data, module.name).source_dir


_current_path = Path(".")


def _description_flag_disabled(application: Application) -> bool:
    """Check if the description feature is disabled for the application"""
    # 仅非云原生应用可以禁用应用描述文件
    return application.type != ApplicationType.CLOUD_NATIVE and not application.feature_flag.has_feature(
        AppFeatureFlag.APPLICATION_DESCRIPTION
    )


def get_desc_data_by_version(module: Module, operator: str, version_info: VersionInfo) -> Optional[Dict]:
    """Get the app description data by version.

    :param module: The module object
    :param operator: The operator name
    :param version_info: The version info, will be used to read the description file
    :return: the app description data, or None if the file cannot be found
    """
    try:
        metadata_reader = get_metadata_reader(module, operator=operator, source_dir=_current_path)
    except NotImplementedError:
        return None

    if _description_flag_disabled(module.application):
        return None

    try:
        return metadata_reader.get_app_desc(version_info)
    except GetAppYamlError:
        return None


def get_deploy_desc_handler_by_version(
    module: Module, operator: str, version_info: VersionInfo, source_dir: Path = _current_path
) -> DeployDescHandler:
    """Get the description handler for the given module and version.

    :param module: The module object
    :param operator: The operator name
    :param version_info: The version info, will be used to read the description file
    :param source_dir: The source directory path to find the description file
    :return: The handler instance
    :raise InitDeployDescHandlerError: When fail to initialize the handler instance
    """
    try:
        metadata_reader = get_metadata_reader(module, operator=operator, source_dir=source_dir)
    except NotImplementedError:
        raise InitDeployDescHandlerError("Unsupported source type")

    # Try to read the "app_desc.yaml" and "Procfile"
    app_desc, app_desc_exc = None, None
    if not _description_flag_disabled(module.application):
        try:
            app_desc = metadata_reader.get_app_desc(version_info)
        except GetAppYamlFormatError as e:
            # The format error in app_desc is not tolerable
            raise InitDeployDescHandlerError(str(e))
        except GetAppYamlError as e:
            app_desc_exc = e

    procfile_data, procfile_exc = None, None
    try:
        procfile_data = metadata_reader.get_procfile(version_info)
    except GetProcfileFormatError as e:
        # The format error in Procfile in not tolerable
        raise InitDeployDescHandlerError(str(e))
    except GetProcfileError as e:
        procfile_exc = e

    # Raise error when none data source can be found
    if not (app_desc or procfile_data):
        msg = []
        if app_desc_exc:
            msg.append(f"[app_desc] {app_desc_exc}")
        if procfile_exc:
            msg.append(f"[Procfile] {procfile_exc}")
        raise InitDeployDescHandlerError("; ".join(msg))

    return get_deploy_desc_handler(app_desc, procfile_data)


def get_source_package_path(deployment: Deployment) -> str:
    """Return the blobstore path for storing source files package"""
    engine_app = deployment.get_engine_app()
    branch = deployment.source_version_name
    revision = deployment.source_revision

    slug_name = f"{engine_app.name}:{branch}:{revision}"
    return f"{engine_app.region}/home/{slug_name}/tar"


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
    except SkipPatchCode as e:
        logger.warning("skip the injection process: %s", e.reason)
        return


def check_source_package(engine_app: EngineApp, package_path: Path, stream: DeployStream):
    """Check module source package, produce warning infos"""
    # Check source package size
    warning_threshold = settings.ENGINE_APP_SOURCE_SIZE_WARNING_THRESHOLD_MB
    size = package_path.stat().st_size
    if size > warning_threshold * 1024 * 1024:
        stream.write_message(
            Style.Warning(
                _(
                    "WARNING: 应用源码包体积过大（>{warning_threshold}MB），将严重影响部署性能，请尝试清理不必要的文件来减小体积。"
                ).format(warning_threshold=warning_threshold)
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
