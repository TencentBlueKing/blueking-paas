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
import copy
import logging
from typing import Dict, Optional, TextIO

import yaml
from django.utils.translation import gettext as _
from typing_extensions import Protocol

from paasng.infras.accounts.models import User
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.declarative.application.constants import APP_CODE_FIELD
from paasng.platform.declarative.application.controller import AppDeclarativeController
from paasng.platform.declarative.application.resources import ApplicationDesc, get_application
from paasng.platform.declarative.application.validations import AppDescriptionSLZ
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.controller import DeploymentDeclarativeController
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.deployment.validations import DeploymentDescSLZ
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.serializers import SMartV1DescriptionSLZ, UniConfigSLZ, validate_desc
from paasng.platform.applications.models import Application
from paasng.platform.modules.constants import SourceOrigin

logger = logging.getLogger(__name__)


def get_desc_handler(json_data: Dict) -> 'DescriptionHandler':
    spec_version = detect_spec_version(json_data)
    if spec_version == AppSpecVersion.VER_1:
        return SMartDescriptionHandler(json_data)
    else:
        return AppDescriptionHandler(json_data)


def detect_spec_version(json_data: Dict) -> AppSpecVersion:
    return AppSpecVersion(json_data.get("spec_version", AppSpecVersion.VER_1.value))


class DescriptionHandler(Protocol):
    @property
    def app_desc(self) -> ApplicationDesc:
        ...

    def get_deploy_desc(self, module_name: Optional[str]) -> DeploymentDesc:
        ...

    def handle_app(self, user: User) -> Application:
        """Handle a YAML config for application initialization

        :param user: User to perform actions as
        """

    def handle_deployment(self, deployment: Deployment):
        """Handle a YAML config file for a deployment

        :param deployment: The related deployment object
        """


class AppDescriptionHandler:
    """A handler to process application's YAML description file(named app_desc.yaml)"""

    @classmethod
    def from_file(cls, fp: TextIO):
        return cls(yaml.safe_load(fp))

    def __init__(self, json_data: Dict):
        """The app_desc.yml json data"""
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
            AppDescriptionSLZ,
            app_desc_json,
            instance,
            context={"app_version": self.json_data.get("app_version"), "spec_version": AppSpecVersion.VER_2},
        )
        return app_desc

    def get_deploy_desc(self, module_name: Optional[str] = None) -> DeploymentDesc:
        module_desc = self.json_data.get("module")
        if "modules" in self.json_data and module_name in self.json_data["modules"]:
            if module_desc is not None:
                logger.warning("Duplicate definition of module information !")
            module_desc = self.json_data["modules"][module_name]
        if not module_desc:
            logger.info('Skip running deployment controller because not content was provided')
            raise DescriptionValidationError({"module": _('内容不能为空')})
        desc = validate_desc(DeploymentDescSLZ, module_desc)
        return desc

    def handle_app(self, user: User, source_origin: Optional[SourceOrigin] = None) -> Application:
        """Handle a YAML config for application initialization

        :param user: User to perform actions as
        """
        json_data = validate_desc(UniConfigSLZ, self.json_data)
        if not json_data["app"]:
            raise DescriptionValidationError({"app": _('内容不能为空')})
        if "module" not in json_data and "modules" not in json_data:
            raise DescriptionValidationError({"modules": _('内容不能为空')})

        controller = AppDeclarativeController(user, source_origin)
        return controller.perform_action(self.app_desc)

    def handle_deployment(self, deployment: Deployment):
        """Handle a YAML config file for a deployment

        :param deployment: The related deployment object
        """
        validate_desc(UniConfigSLZ, self.json_data)

        controller = DeploymentDeclarativeController(deployment)
        controller.perform_action(self.get_deploy_desc(deployment.app_environment.module.name))


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
        instance = get_application(self.json_data, 'app_code')
        # S-mart application always perform a full update by using partial=False
        app_desc, _ = validate_desc(SMartV1DescriptionSLZ, self.json_data, instance, partial=False)
        return app_desc

    def get_deploy_desc(self, module_name: Optional[str] = None) -> DeploymentDesc:
        instance = get_application(self.json_data, 'app_code')
        # S-mart application always perform a full update by using partial=False
        _, deploy_desc = validate_desc(SMartV1DescriptionSLZ, self.json_data, instance, partial=False)
        return deploy_desc

    def handle_app(self, user: User) -> Application:
        """Handle a app config

        :param user: User to perform actions as
        """
        controller = AppDeclarativeController(user)
        return controller.perform_action(self.app_desc)

    def handle_deployment(self, deployment: Deployment):
        """Handle a deployment config

        :param deployment: The related deployment object
        """
        controller = DeploymentDeclarativeController(deployment)
        controller.perform_action(self.get_deploy_desc(None))
