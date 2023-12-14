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
"""Manages Application's specifications

"Specification" describes an application. It includes many aspects, such as "was able to create new modules"、
"has enabled engine service" etc.
"""
import logging
from abc import ABC
from typing import Any, Dict, Type

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from paasng.core.region.models import get_region
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template

from .constants import ApplicationType
from .models import Application

logger = logging.getLogger(__name__)


class AppSpecs:
    """Read application's specifications which were determined by below factors:

    - Application's type
    - Application's region config
    - Whether application was created via S-Mart package
    - etc.
    """

    def __init__(self, application: Application):
        self.application = application
        self.type_specs = AppTypeSpecs.get_by_type(ApplicationType(application.type))
        self.region = get_region(application.region)

    @property
    def engine_enabled(self) -> bool:
        """Whether an application has enabled engine service"""
        return self.type_specs.engine_enabled

    @property
    def can_create_extra_modules(self) -> bool:
        """Whether an application can create new modules"""
        if not self.region.mul_modules_config.creation_allowed:
            return False
        # S-mart 应用、插件应用，不允许新增模块
        if self.application.is_smart_app or self.application.is_plugin_app:
            return False
        return self.type_specs.can_create_extra_modules

    @property
    def require_templated_source(self) -> bool:
        """Whether an application must choose source template"""
        # 插件应用不需要模板
        if self.application.is_plugin_app:
            return False
        return self.type_specs.require_templated_source

    @property
    def language_by_default(self) -> str:
        # 插件应用的默认语言为 python
        if self.application.is_plugin_app:
            return "Python"
        return self.type_specs.language_by_default

    @property
    def preset_services(self) -> Dict[str, Dict]:
        if self.application.is_plugin_app:
            return settings.PRESET_SERVICES_BY_APP_TYPE.get("bk_plugin", {})
        return self.type_specs.preset_services

    @property
    def confirm_required_when_publish(self) -> bool:
        """Whether an extra confirmation is required when publishing application to market"""
        module = self.application.get_default_module()
        if self.type_specs.engine_enabled:
            # 非精简版应用，依赖模板配置是否允许发布到市场
            try:
                # 允许发布到市场的模板则不需要发布前确认
                return not Template.objects.get(
                    name=module.source_init_template, type=TemplateType.NORMAL
                ).market_ready
            except ObjectDoesNotExist:
                logger.warning(f'Unable to get metadata, invalid template name: "{module.source_init_template}"')
        # 老的不再使用的模板已经被删除，默认发布到市场前不需要确认
        return False

    @property
    def market_published(self) -> bool:
        """Whether an application has been published to market"""
        try:
            return self.application.market_config.enabled
        except ObjectDoesNotExist:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_enabled": self.engine_enabled,
            "can_create_extra_modules": self.can_create_extra_modules,
            "require_templated_source": self.require_templated_source,
            "confirm_required_when_publish": self.confirm_required_when_publish,
            "market_published": self.market_published,
        }


class AppTypeSpecs(ABC):
    """App's specifications derived from type"""

    type_: ApplicationType

    # Whether engine-related functionalities were enabled, such as deploy、logging etc.
    engine_enabled: bool = True

    # Whether an application can create new modules besides the "default" one
    can_create_extra_modules: bool = True

    # Whether an application needs templated source codes when being created
    require_templated_source: bool = True

    # When user hasn't provided any source template, use this language by default
    language_by_default: str = ""

    _spec_types: Dict[ApplicationType, Type["AppTypeSpecs"]] = {}

    @classmethod
    def __init_subclass__(cls) -> None:
        """Register all subclasses"""
        super().__init_subclass__()
        if cls.type_:
            cls._spec_types[cls.type_] = cls

    @classmethod
    def get_by_type(cls, type_: ApplicationType) -> "AppTypeSpecs":
        """Get Spec type by application type"""
        #
        try:
            return cls._spec_types[type_]()
        except KeyError:
            raise RuntimeError(f"{type_} is not a valid application type, no TypeSpecs can be found!")

    @property
    def preset_services(self) -> Dict[str, Dict]:
        """Bind default module with below services when application was created"""
        services = settings.PRESET_SERVICES_BY_APP_TYPE.get(self.type_.value, {})
        return services


class DefaultTypeSpecs(AppTypeSpecs):
    """Specs for default type"""

    type_ = ApplicationType.DEFAULT
    engine_enabled = True
    can_create_extra_modules = True
    require_templated_source = True


class EnginelessAppTypeSpecs(AppTypeSpecs):
    """Specs for engineless_app type"""

    type_ = ApplicationType.ENGINELESS_APP
    engine_enabled = False
    can_create_extra_modules = False
    require_templated_source = False


class CloudNativeTypeSpecs(AppTypeSpecs):
    """Specs for cloud-native type"""

    type_ = ApplicationType.CLOUD_NATIVE
    engine_enabled = True
    can_create_extra_modules = True
    require_templated_source = False
