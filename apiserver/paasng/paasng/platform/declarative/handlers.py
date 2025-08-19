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

import copy
import logging
from typing import Callable, Dict, Literal, Optional, TextIO

import yaml
from django.utils.translation import gettext as _
from typing_extensions import Protocol, TypeAlias

from paasng.core.tenant.utils import AppTenantInfo
from paasng.infras.accounts.models import User
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.bkapp_model.entities.proc_env_overlays import ReplicasOverlay
from paasng.platform.bkapp_model.entities.v1alpha2 import BkAppEnvOverlay
from paasng.platform.bkapp_model.form_overrides.replicas import generate_replica_overrides
from paasng.platform.declarative.application.constants import APP_CODE_FIELD, CNATIVE_APP_CODE_FIELD
from paasng.platform.declarative.application.controller import AppDeclarativeController
from paasng.platform.declarative.application.resources import ApplicationDesc, get_application
from paasng.platform.declarative.application.validations import v2 as app_spec_v2
from paasng.platform.declarative.application.validations import v3 as app_spec_v3
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.controller import (
    DeployHandleResult,
    DeploymentDeclarativeController,
    handle_procfile_procs,
)
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.deployment.validations import v2 as deploy_spec_v2
from paasng.platform.declarative.deployment.validations import v3 as deploy_spec_v3
from paasng.platform.declarative.exceptions import DescriptionValidationError, UnsupportedSpecVer
from paasng.platform.declarative.serializers import (
    UniConfigSLZ,
    validate_desc,
    validate_procfile_procs,
)
from paasng.platform.engine.constants import ReplicasPolicy
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.modules.constants import SourceOrigin
from paasng.utils.structure import NOTSET

logger = logging.getLogger(__name__)


def get_desc_handler(json_data: Dict) -> "DescriptionHandler":
    """Get the handler for handling description data, it handles the app
    level logics, see `get_deploy_desc_handler` for deployment level handler.

    :param json_data: The description data in dict format.
    """
    try:
        spec_version = detect_spec_version(json_data)
    except ValueError as e:
        return UnsupportedVerDescriptionHandler(version=str(e))

    match spec_version:
        case AppSpecVersion.VER_2:
            return AppDescriptionHandler(json_data)
        case AppSpecVersion.VER_3:
            return CNativeAppDescriptionHandler(json_data)
        case AppSpecVersion.UNSPECIFIED:
            return NoVerDescriptionHandler()
        case _:
            return UnsupportedVerDescriptionHandler(version=str(spec_version.value))


def detect_spec_version(json_data: Dict) -> AppSpecVersion:
    """Detect the spec version from the input data.

    :return: The version.
    :raise ValueError: When the version is specified but it's value is invalid.
    """
    if spec_version := json_data.get("spec_version") or json_data.get("specVersion"):
        try:
            return AppSpecVersion(spec_version)
        except ValueError:
            raise ValueError(spec_version)

    # The spec ver "1" use no version field while the "app_code" field is always presented.
    if "app_code" in json_data:
        return AppSpecVersion.VER_1

    return AppSpecVersion.UNSPECIFIED


class DescriptionHandler(Protocol):
    @property
    def app_desc(self) -> ApplicationDesc: ...

    @property
    def app_tenant(self) -> AppTenantInfo: ...

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        """Handle a YAML config for application initialization

        :param user: User to perform actions as
        :param source_origin: 源码来源
        """


class CNativeAppDescriptionHandler:
    """A handler to process cnative application's YAML description file(named app_desc.yaml)"""

    @classmethod
    def from_file(cls, fp: TextIO):
        return cls(yaml.safe_load(fp))

    def __init__(self, json_data: Dict):
        self.json_data = json_data

    @property
    def app_desc(self) -> ApplicationDesc:
        """Turn json data into application description object

        :raises: DescriptionValidationError when input is invalid
        """
        app_desc_json = copy.deepcopy(self.json_data.get("app", {}))
        app_desc_json["modules"] = self.json_data.get("modules", {})
        # 根据约定, 我们允许在 app_desc.yaml 同级目录下, 以 logo.png 存储当前 S-Mart 的 logo, 该文件的内容会被读取到 meta_info.logo_b64data
        # 为了保证后续逻辑只需遵循 app_desc 规范, 在正式解析 app_desc 之前, 我们需要重命名 logo_b64data 字段为 market.logo_b64data
        if logo_b64data := self.json_data.get("logoB64data"):
            app_desc_json.setdefault("market", {}).setdefault("logoB64data", logo_b64data)

        instance = get_application(app_desc_json, CNATIVE_APP_CODE_FIELD)
        app_desc = validate_desc(
            app_spec_v3.AppDescriptionSLZ,
            app_desc_json,
            instance,
            context={"app_version": self.json_data.get("appVersion"), "spec_version": AppSpecVersion.VER_3},
        )
        return app_desc

    @property
    def app_tenant(self) -> AppTenantInfo:
        """Turn json data into application tenant object"""
        return AppTenantInfo(**self.json_data["tenant"])

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        """Handle a YAML config for application initialization

        :param user: User to perform actions as
        """
        controller = AppDeclarativeController(user, self.app_tenant, source_origin)
        return controller.perform_action(self.app_desc)


class AppDescriptionHandler:
    """A handler to process application's YAML description file(named app_desc.yaml)"""

    @classmethod
    def from_file(cls, fp: TextIO):
        return cls(yaml.safe_load(fp))

    def __init__(self, json_data: Dict):
        self.json_data = json_data

    @property
    def app_desc(self) -> ApplicationDesc:
        """Turn json data into application description object

        :raises: DescriptionValidationError when input is invalid
        """
        app_desc_json = copy.deepcopy(self.json_data.get("app", {}))
        app_desc_json["modules"] = self.json_data.get("modules", {})
        # 根据约定, 我们允许在 app_desc.yaml 同级目录下, 以 logo.png 存储当前 S-Mart 的 logo, 该文件的内容会被读取到 meta_info.logo_b64data
        # 为了保证后续逻辑只需遵循 app_desc 规范, 在正式解析 app_desc 之前, 我们需要重命名 logo_b64data 字段为 market.logo_b64data
        if "logo_b64data" in self.json_data:
            app_desc_json.setdefault("market", {}).setdefault("logo_b64data", self.json_data["logo_b64data"])

        instance = get_application(app_desc_json, APP_CODE_FIELD)
        # TODO: 兼容获取非源码包部署的应用的版本
        app_desc = validate_desc(
            app_spec_v2.AppDescriptionSLZ,
            app_desc_json,
            instance,
            context={"app_version": self.json_data.get("app_version"), "spec_version": AppSpecVersion.VER_2},
        )
        return app_desc

    @property
    def app_tenant(self) -> AppTenantInfo:
        return AppTenantInfo(**self.json_data["tenant"])

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        """Handle a YAML config for application initialization

        :param user: User to perform actions as
        """
        json_data = validate_desc(UniConfigSLZ, self.json_data)
        if not json_data["app"]:
            raise DescriptionValidationError({"app": _("内容不能为空")})
        if "module" not in json_data and "modules" not in json_data:
            raise DescriptionValidationError({"modules": _("内容不能为空")})

        controller = AppDeclarativeController(user, self.app_tenant, source_origin)
        return controller.perform_action(self.app_desc)


class UnsupportedVerDescriptionHandler:
    """A special handler, raise error if the version is not supported."""

    def __init__(self, version: str):
        self.message = f'App spec version "{version}" is not supported, please use a valid version like "3".'

    @property
    def app_desc(self) -> ApplicationDesc:
        raise DescriptionValidationError(self.message)

    @property
    def app_tenant(self) -> AppTenantInfo:
        raise DescriptionValidationError("Missing tenant configuration information")

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        raise DescriptionValidationError(self.message)


class NoVerDescriptionHandler:
    """A special handler, raise error if no version is specified."""

    message = "No spec version is specified, please set the spec version to a valid value."

    @property
    def app_desc(self) -> ApplicationDesc:
        raise DescriptionValidationError(self.message)

    @property
    def app_tenant(self) -> AppTenantInfo:
        raise DescriptionValidationError("Missing tenant configuration information")

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        raise DescriptionValidationError(self.message)


###
# Deploy related functions
###


def get_deploy_desc_handler(
    desc_data: Optional[Dict] = None, procfile_data: Optional[Dict] = None
) -> "DeployDescHandler":
    """Get the handler for handling description data when performing new deployment.

    :param desc_data: The description data in dict format, optional
    :param procfile_data: The "Procfile" data in dict format, format: {<proc_type>: <command>}
    :raise ValueError: When the input data is invalid for creating a handler.
    """
    if not (desc_data or procfile_data):
        raise ValueError("the app desc and procfile data can't be both empty")

    if not desc_data:
        # Only procfile data is provided, use the handler to handle processes data only
        assert procfile_data
        return ProcfileOnlyDeployDescHandler(procfile_data)

    try:
        _func = get_desc_getter_func(desc_data)
    except UnsupportedSpecVer as e:
        # When the spec version is not supported and no procfile data is provided,
        # raise an error to inform the user.
        if not procfile_data:
            raise ValueError("the procfile data is empty and the app desc data is invalid, detail: {}".format(str(e)))
        else:
            return ProcfileOnlyDeployDescHandler(procfile_data)

    return DefaultDeployDescHandler(desc_data, procfile_data, _func)


def get_deploy_desc_by_module(desc_data: Dict, module_name: str) -> DeploymentDesc:
    """Get the deploy desc object by module name

    :param desc_data: The description data in dict format, may contains multiple modules
    :param module_name: The module name
    :raise DescriptionValidationError: When the input data is invalid
    """
    try:
        _func = get_desc_getter_func(desc_data)
    except UnsupportedSpecVer as e:
        raise DescriptionValidationError(str(e))
    return _func(desc_data, module_name)


def get_source_dir_from_desc(desc_data: Dict, module_name: str) -> str:
    """Get the source directory specified in the description data by module name.

    :param desc_data: The description data in dict format, may contains multiple modules
    :param module_name: The module name
    :return: The source directory
    """
    try:
        _func = get_desc_getter_func(desc_data)
    except UnsupportedSpecVer:
        # When the spec version is not supported, use the default value
        return ""
    return _func(desc_data, module_name).source_dir


class DeployDescHandler(Protocol):
    def handle(self, deployment: Deployment) -> DeployHandleResult:
        """Handle a deployment object.

        :param deployment: The deployment object
        """
        ...


# A simple function type that get the deploy description object from the json data.
DescGetterFunc: TypeAlias = Callable[[Dict, str], DeploymentDesc]


def get_desc_getter_func(desc_data: Dict) -> DescGetterFunc:
    """Get the description getter function by current desc data.

    :raise UnsupportedSpecVer: When the spec version is not supported.
    """
    try:
        spec_version = detect_spec_version(desc_data)
    except ValueError as e:
        raise UnsupportedSpecVer(f'app spec version "{str(e)}" is not supported')

    match spec_version:
        case AppSpecVersion.VER_2:
            return deploy_desc_getter_v2
        case AppSpecVersion.VER_3:
            return deploy_desc_getter_v3
        case AppSpecVersion.UNSPECIFIED:
            raise UnsupportedSpecVer("no spec version is specified")
        case _:
            raise UnsupportedSpecVer(f'app spec version "{spec_version.value}" is not supported')


class DefaultDeployDescHandler:
    """The default handler for handling deployment description data.

    :param json_data: The description data in dict format
    :param procfile_data: The Procfile data in dict format, can be none
    :param desc_getter: The function to get the deployment desc object
    """

    def __init__(self, json_data: Dict, procfile_data: Optional[Dict], desc_getter: DescGetterFunc):
        self.json_data = json_data
        self.procfile_data = procfile_data
        self.desc_getter = desc_getter

    def handle(self, deployment: Deployment) -> DeployHandleResult:
        desc = self.desc_getter(self.json_data, deployment.app_environment.module.name)

        if deployment.advanced_options.replicas_policy == ReplicasPolicy.WEB_FORM_PRIORITY:
            apply_form_replicas_overrides(desc, deployment.app_environment)

        procfile_procs = validate_procfile_procs(self.procfile_data) if self.procfile_data else None
        return DeploymentDeclarativeController(deployment).perform_action(desc, procfile_procs)


class ProcfileOnlyDeployDescHandler:
    """The handler for handling the procfile data only.

    :param procfile_data: The Procfile data in dict format
    """

    def __init__(self, procfile_data: Dict):
        self.procfile_data = procfile_data

    def handle(self, deployment: Deployment) -> DeployHandleResult:
        procfile_procs = validate_procfile_procs(self.procfile_data)
        return handle_procfile_procs(deployment, procfile_procs)


def deploy_desc_getter_v2(json_data: Dict, module_name: str) -> DeploymentDesc:
    """Get the deployment desc object, spec ver 2."""
    validate_desc(UniConfigSLZ, json_data)
    desc_data = _find_module_desc_data(json_data, module_name, "dict")
    return validate_desc(deploy_spec_v2.DeploymentDescSLZ, desc_data)


def deploy_desc_getter_v3(json_data: Dict, module_name: str) -> DeploymentDesc:
    """Get the deployment desc object, spec ver 3."""
    desc_data = _find_module_desc_data(json_data, module_name, "list")
    return validate_desc(deploy_spec_v3.DeploymentDescSLZ, desc_data)


def apply_form_replicas_overrides(desc: DeploymentDesc, env: ModuleEnvironment):
    """实施表单副本数覆盖策略，确保部署描述对象在部署时, 以表单配置的副本数为准

    :param desc: the deployment desc object which will be adjusted
    :param env: The environment object
    """
    replica_overrides = generate_replica_overrides(
        env.module, process_names=[proc.name for proc in desc.spec.processes]
    )

    if not replica_overrides:
        return

    # 1. 设置 spec.processes[].replicas
    for proc in desc.spec.processes:
        if proc.name in replica_overrides:
            proc.replicas = replica_overrides[proc.name]
            replica_overrides.pop(proc.name)

    # 2. 设置 spec.env_overlay.replicas
    env_overlay_replicas_maps = {}
    if desc.spec.env_overlay and desc.spec.env_overlay.replicas:  # type: ignore[union-attr]
        env_overlay_replicas_maps = {(r.process, r.env_name): r.count for r in desc.spec.env_overlay.replicas}  # type: ignore[union-attr]

    env_overlay_replicas_maps.update(replica_overrides)  # type: ignore[arg-type]

    env_overlay_replicas_maps = {
        (process, env_name): count
        for (process, env_name), count in env_overlay_replicas_maps.items()
        if isinstance(count, int)
    }

    if env_overlay_replicas_maps:
        desc.spec.env_overlay = desc.spec.env_overlay or BkAppEnvOverlay()
        desc.spec.env_overlay.replicas = [  # type: ignore[union-attr]
            ReplicasOverlay(env_name=env_name, process=process, count=count)
            for (process, env_name), count in env_overlay_replicas_maps.items()
        ]
    elif desc.spec.env_overlay:
        desc.spec.env_overlay.replicas = NOTSET  # type: ignore[union-attr]


def _find_module_desc_data(
    json_data: Dict,
    module_name: Optional[str],
    modules_data_type: Literal["list", "dict"],
) -> Dict:
    """Find a module's desc data in the json data. This function can be used in both v2 and v3
    because them have similar(but slightly different) structure.

    In the `json_data` 2 fields are used to store the module data:

    - "module": contains desc data of the default module.
    - "modules": contains desc data of multiple modules, use a list(v3) or dict(v2) format.

    :param modules_data_type: The data type that holds the modules data, v2 using dict, v3 using list.
    """
    if not module_name:
        desc_data = json_data.get("module")
        if not desc_data:
            raise DescriptionValidationError({"module": _("模块配置内容不能为空")})
        return desc_data

    # "module_name" is not None, find the desc data in the json data.
    desc_data = None
    # When "modules" is provided, find the desc in it's content by module name
    if modules_data := json_data.get("modules"):
        # Use different approach for different module data type
        if modules_data_type == "dict":
            desc_data = modules_data.get(module_name)
            existed_modules = ", ".join(modules_data.keys())
        elif modules_data_type == "list":
            desc_data = next((m for m in modules_data if m["name"] == module_name), None)
            existed_modules = ", ".join(m["name"] for m in modules_data)
        else:
            raise ValueError("Wrong modules data type")

        # Use the value in the "module" field as a fallback
        desc_data = desc_data or json_data.get("module")
        if not desc_data:
            raise DescriptionValidationError(
                {"modules": _("未找到 {} 模块的配置，当前已配置模块为 {}").format(module_name, existed_modules)}
            )

    # The "modules" field is not provided, use the value in the "module" field
    if not desc_data:
        desc_data = json_data.get("module")

    if not desc_data:
        raise DescriptionValidationError({"module": _("模块配置内容不能为空")})
    return desc_data
