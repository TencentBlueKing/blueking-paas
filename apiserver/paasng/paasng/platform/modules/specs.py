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
"""Manages Module's specifications

"Specification" describes an module. It includes many aspects, such as "use templated source code" etc.
"""
from abc import ABC
from typing import Any, Dict, Type

from paasng.engine.constants import RuntimeType
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module


def source_origin_property(name: str):
    """Make a property object which read values from 'self.source_origin_specs'
    TODO: Replace with descriptor class
    """
    return property(lambda self: getattr(self.source_origin_specs, name))


class ModuleSpecs:
    """Read module's specifications which were determined by below factors:

    - Module's Application specs
    - Module's source origin
    - Other related properties
    """

    def __init__(self, module: Module):
        self.module = module
        self.app_specs = AppSpecs(module.application)
        self.source_origin_specs = SourceOriginSpecs.get(SourceOrigin(module.get_source_origin()))

    has_template_code = source_origin_property('has_template_code')
    deploy_via_package = source_origin_property('deploy_via_package')

    @property
    def templated_source_enabled(self) -> bool:
        """Whether current module has templated source"""
        # TODO: Do not read value from application, store metadata in module object itself
        return self.app_specs.require_templated_source and self.has_template_code

    @property
    def runtime_type(self) -> RuntimeType:
        if runtime_type := getattr(self.source_origin_specs, "runtime_type", None):
            return runtime_type
        return RuntimeType(self.module.runtime_type)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'templated_source_enabled': self.templated_source_enabled,
            "runtime_type": self.runtime_type.value,
        }


class SourceOriginSpecs(ABC):
    """Module's specifications derived from SourceOrigin"""

    source_origin: SourceOrigin

    # Describe the type of runtime system
    runtime_type: RuntimeType

    # Whether current module has template code, the code was usually initialized during module creation
    has_template_code: bool = True

    # Whether module was deployed via source package file
    deploy_via_package: bool = False

    _spec_types: Dict[SourceOrigin, Type['SourceOriginSpecs']] = {}

    @classmethod
    def __init_subclass__(cls) -> None:
        """Register all subclasses"""
        super().__init_subclass__()
        if cls.source_origin:
            cls._spec_types[cls.source_origin] = cls

    @classmethod
    def get(cls, source_origin: SourceOrigin) -> 'SourceOriginSpecs':
        try:
            return cls._spec_types[source_origin]()
        except KeyError:
            raise RuntimeError(f'{source_origin} is not valid, no SourceOriginSpecs can be found!')


class AuthorizedVcsSpecs(SourceOriginSpecs):
    """Specs for source_origin: AUTHORIZED_VCS"""

    source_origin = SourceOrigin.AUTHORIZED_VCS
    has_template_code = True
    deploy_via_package = False


class PackageMixin:
    """Stores common mixin properties for external package based source origins"""

    runtime_type = RuntimeType.BUILDPACK
    has_template_code = False
    deploy_via_package = True


class BkLessCodeSpecs(PackageMixin, SourceOriginSpecs):
    """Specs for source_origin: BK_LESS_CODE"""

    source_origin = SourceOrigin.BK_LESS_CODE


class SMartSpecs(PackageMixin, SourceOriginSpecs):
    """Specs for source_origin: S_MART"""

    source_origin = SourceOrigin.S_MART


class ImageRegistrySpecs(SourceOriginSpecs):
    """Specs for source_origin: IMAGE_REGISTRY"""

    source_origin = SourceOrigin.IMAGE_REGISTRY
    runtime_type = RuntimeType.CUSTOM_IMAGE
    has_template_code = False
    deploy_via_package = False


class SceneSpecs(SourceOriginSpecs):
    """Specs for source_origin: SCENE"""

    source_origin = SourceOrigin.SCENE
    runtime_type = RuntimeType.BUILDPACK
    has_template_code = True
    deploy_via_package = False
