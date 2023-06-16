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
"""This module provides manual relational queries"""
from typing import Optional, Type, Union, overload

from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module


class ModuleAttrFromID:
    """A descriptor which make `{owner}.module` available by reading from "_structured_app" property."""

    key_field = 'module_id'

    @overload
    def __get__(self, instance: None, owner: None) -> 'ModuleAttrFromID':
        ...

    @overload
    def __get__(self, instance: object, owner: Type) -> Module:
        ...

    def __get__(self, instance, owner: Optional[Type] = None) -> Union['ModuleAttrFromID', Module]:
        """Read module value

        :raise: ValueError when instance was not initialized with structured data
        :raise: AppSubResourceNotFound when no result can be found
        """
        if not instance:
            return self

        module_id = getattr(instance, self.key_field)
        return Module.objects.get(pk=module_id)


class ModuleEnvAttrFromID:
    """A descriptor which make `{owner}.environment` available by reading from "_structured_app" property."""

    key_field = 'environment_id'

    @overload
    def __get__(self, instance: None, owner: None) -> 'ModuleEnvAttrFromID':
        ...

    @overload
    def __get__(self, instance: object, owner: Type) -> ModuleEnvironment:
        ...

    def __get__(self, instance, owner: Optional[Type] = None) -> Union['ModuleEnvAttrFromID', ModuleEnvironment]:
        """Read environment value

        :raise: ValueError when instance was not initialized with structured data
        :raise: AppSubResourceNotFound when no result can be found
        """
        if not instance:
            return self

        env_id = getattr(instance, self.key_field)
        return ModuleEnvironment.objects.get(pk=env_id)


class ModuleEnvAttrFromName:
    """A descriptor which make `{owner}.environment` available by reading from "_structured_app" property.

    - both `module_id` and `environment_name` fields are required.
    """

    key_field = 'environment_name'
    module_key_field = 'module_id'

    @overload
    def __get__(self, instance: None, owner: None) -> 'ModuleEnvAttrFromName':
        ...

    @overload
    def __get__(self, instance: object, owner: Type) -> ModuleEnvironment:
        ...

    def __get__(self, instance, owner: Optional[Type] = None) -> Union['ModuleEnvAttrFromName', ModuleEnvironment]:
        """Read environment value

        :raise: ValueError when instance was not initialized with structured data
        :raise: AppSubResourceNotFound when no result can be found
        """
        if not instance:
            return self

        module_id = getattr(instance, self.module_key_field)
        env_name = getattr(instance, self.key_field)

        return ModuleEnvironment.objects.get(module_id=module_id, environment=env_name)
