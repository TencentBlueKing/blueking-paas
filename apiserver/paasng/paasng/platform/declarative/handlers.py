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

from paasng.infras.accounts.models import User
from paasng.platform.applications.models import Application
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
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.serializers import (
    SMartV1DescriptionSLZ,
    UniConfigSLZ,
    validate_desc,
    validate_procfile_procs,
)
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.modules.constants import SourceOrigin

logger = logging.getLogger(__name__)


def get_desc_handler(json_data: Dict) -> "DescriptionHandler":
    """Get the handler for handling description data, this handler handle the app
    level logics, see `get_deploy_desc_handler` for deployment level handler.

    :param json_data: The description data in dict format.
    """
    spec_version = detect_spec_version(json_data)
    # TODO 删除 SMartDescriptionHandler 分支. VER_1 存量版本基本不再支持
    if spec_version == AppSpecVersion.VER_1:
        return SMartDescriptionHandler(json_data)
    elif spec_version == AppSpecVersion.VER_2:
        return AppDescriptionHandler(json_data)
    else:
        # 对应 AppSpecVersion.VER_3
        return CNativeAppDescriptionHandler(json_data)


def detect_spec_version(json_data: Dict) -> AppSpecVersion:
    if spec_version := json_data.get("spec_version") or json_data.get("specVersion"):
        return AppSpecVersion(spec_version)
    return AppSpecVersion.VER_1


class DescriptionHandler(Protocol):
    @property
    def app_desc(self) -> ApplicationDesc: ...

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

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        """Handle a YAML config for application initialization

        :param user: User to perform actions as
        """
        controller = AppDeclarativeController(user, source_origin)
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

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        """Handle a YAML config for application initialization

        :param user: User to perform actions as
        """
        json_data = validate_desc(UniConfigSLZ, self.json_data)
        if not json_data["app"]:
            raise DescriptionValidationError({"app": _("内容不能为空")})
        if "module" not in json_data and "modules" not in json_data:
            raise DescriptionValidationError({"modules": _("内容不能为空")})

        controller = AppDeclarativeController(user, source_origin)
        return controller.perform_action(self.app_desc)


class SMartDescriptionHandler:
    """A handler to process S-Mart app description file"""

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
        instance = get_application(self.json_data, "app_code")
        # S-mart application always perform a full update by using partial=False
        app_desc, _ = validate_desc(SMartV1DescriptionSLZ, self.json_data, instance, partial=False)
        return app_desc

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        """Handle a app config

        :param user: User to perform actions as
        """
        controller = AppDeclarativeController(user)
        return controller.perform_action(self.app_desc)


def get_deploy_desc_handler(
    desc_data: Optional[Dict] = None, procfile_data: Optional[Dict] = None
) -> "DeployDescHandler":
    """Get the handler for handling description data when performing new deployment.

    :param desc_data: The description data in dict format, optional
    :param procfile_data: The "Procfile" data in dict format, format: {"type": "command"}
    """
    if not (desc_data or procfile_data):
        raise ValueError("json_data and procfile_data can't be both None")

    if not desc_data:
        # Only procfile data is provided, use the handler to handel processes data only
        assert procfile_data
        return ProcfileOnlyDeployDescHandler(procfile_data)
    return DefaultDeployDescHandler(desc_data, procfile_data, get_desc_getter_func(desc_data))


def get_deploy_desc_by_module(desc_data: Dict, module_name: str) -> DeploymentDesc:
    """Get the deploy desc object by module name

    :param desc_data: The description data in dict format, may contains multiple modules
    :param module_name: The module name
    """
    return get_desc_getter_func(desc_data)(desc_data, module_name)


class DeployDescHandler(Protocol):
    def handle(self, deployment: Deployment) -> DeployHandleResult:
        """Handle a deployment object.

        :param deployment: The deployment object
        """
        ...


# A simple function type that get the deploy description object from the json data.
DescGetterFunc: TypeAlias = Callable[[Dict, str], DeploymentDesc]


def get_desc_getter_func(desc_data: Dict) -> DescGetterFunc:
    """Get the description getter function by current desc data."""
    spec_version = detect_spec_version(desc_data)
    # TODO: 删除此分支，VER_1 存量版本基本不再支持
    if spec_version == AppSpecVersion.VER_1:
        desc_getter = deploy_desc_getter_v1
    elif spec_version == AppSpecVersion.VER_2:
        desc_getter = deploy_desc_getter_v2
    else:
        desc_getter = deploy_desc_getter_v3
    return desc_getter


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


def deploy_desc_getter_v1(json_data: Dict, module_name: str) -> DeploymentDesc:
    """Get the deployment desc object, spec ver 1."""
    instance = get_application(json_data, "app_code")
    # S-mart application always perform a full update by using partial=False
    _, deploy_desc = validate_desc(SMartV1DescriptionSLZ, json_data, instance, partial=False)
    return deploy_desc


def deploy_desc_getter_v2(json_data: Dict, module_name: str) -> DeploymentDesc:
    """Get the deployment desc object, spec ver 2."""
    validate_desc(UniConfigSLZ, json_data)
    desc_data = _find_module_desc_data(json_data, module_name, "dict")
    return validate_desc(deploy_spec_v2.DeploymentDescSLZ, desc_data)


def deploy_desc_getter_v3(json_data: Dict, module_name: str) -> DeploymentDesc:
    """Get the deployment desc object, spec ver 3."""
    desc_data = _find_module_desc_data(json_data, module_name, "list")
    return validate_desc(deploy_spec_v3.DeploymentDescSLZ, desc_data)


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
