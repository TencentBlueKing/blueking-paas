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
"""Base data model from PaaS"""
from typing import Dict, Iterable, List, Optional, Type, Union, overload
from uuid import UUID

import cattr
from attrs import Factory, asdict, define

from paas_wl.platform.external.client import get_local_plat_client

from .constants import ApplicationType
from .exceptions import AppSubResourceNotFound, InstanceInPlaceNotFound, PermInPlaceNotFound, UnsupportedPermissionName


@define
class Application:
    id: UUID
    type: ApplicationType
    region: str
    code: str
    name: str


@define
class Module:
    id: UUID
    application: Application
    name: str

    @property
    def application_id(self) -> UUID:
        return self.application.id


@define
class ModuleEnv:
    id: int
    application: Application
    module: Module
    environment: str
    engine_app_id: UUID
    is_offlined: bool  # TODO: remove this property after migration of deployment related data

    @property
    def application_id(self) -> UUID:
        return self.application.id

    @property
    def module_id(self) -> UUID:
        return self.module.id


@define
class EngineAppPlain:
    """A plain EngineApp model"""

    id: UUID
    application: Application
    name: str

    @property
    def application_id(self) -> UUID:
        return self.application.id


@define
class InstancesInPlace:
    """Stores a collection of instances.

    A "instance-in-place" is a special object which was provided by platform via static data, such as
    JWT token in each request.

    TODO: All algorithms can be replaced by adopting an in-memory database if more instances were involved
    in the future.
    """

    applications: List[Application] = Factory(list)
    modules: List[Module] = Factory(list)
    module_envs: List[ModuleEnv] = Factory(list)
    engine_apps: List[EngineAppPlain] = Factory(list)

    def query_engine_app(self, code: str, module_name: str, environment: str) -> EngineAppPlain:
        """Query for an EngineAppPlain instance by parameters

        :param code: application code
        :param module_name: name of application module
        :param environment: name of environment
        :raises: InstanceInPlaceNotFound exception when no result can be found
        """
        app = self.get_application_by_code(code)
        module = self.get_module_by_name(app, module_name)
        env = self.get_module_env_by_environment(module, environment)
        return self.get_engine_app_by_id(env.engine_app_id)

    def get_application_by_code(self, code: str) -> Application:
        """Get an Application object by code"""
        for app in self.applications:
            if app.code == code:
                return app
        raise InstanceInPlaceNotFound(f'Application with code="{code}" not found')

    def get_module_by_name(self, application: Application, module_name: str) -> Module:
        """Get a Module object by name"""
        for module in self.modules:
            if module.application_id == application.id and module.name == module_name:
                return module
        raise InstanceInPlaceNotFound(f'Module with name="{module_name}" not found')

    def get_module_env_by_environment(self, module: Module, environment: str) -> ModuleEnv:
        """Get a ModuleEnv object by environment name"""
        for module_env in self.module_envs:
            if module_env.module_id == module.id and module_env.environment == environment:
                return module_env
        raise InstanceInPlaceNotFound(f'ModuleEnv with environment="{environment}" not found')

    def get_engine_app_by_id(self, pk: UUID) -> EngineAppPlain:
        """Get an EngineAppPlain object by primary key(id)"""
        for engine_app in self.engine_apps:
            if engine_app.id == pk:
                return engine_app
        raise InstanceInPlaceNotFound(f'EngineAppPlain with id="{pk}" not found')


class PermissionMixin:
    detail: Dict[str, bool]

    def check_allowed(self, name: str) -> bool:
        """Check if an action is allowed

        :param name: action/permission name
        :return: whether current action is allowed
        :raise: `UnsupportedPermissionName` when name is invalid
        """
        try:
            return self.detail[name]
        except KeyError:
            raise UnsupportedPermissionName(f'"{name}" is not a valid permission name, choices: {self.detail}')


@define
class ApplicationPermissions(PermissionMixin):
    """The detailed permission data on application"""

    application: Application
    detail: Dict[str, bool]


@define
class SitePermissions(PermissionMixin):
    """The detailed permission data on site"""

    role: str
    detail: Dict[str, bool]


@define
class PermissionsInPlace:
    """Stores a collection of user permissions on instances."""

    application_perms: List[ApplicationPermissions] = Factory(list)
    site_perms: Optional[SitePermissions] = None

    def get_application_perms(self, application: Application) -> ApplicationPermissions:
        """Get a group of permission check results by application"""
        for perms_obj in self.application_perms:
            if perms_obj.application == application:
                return perms_obj
        raise PermInPlaceNotFound(f'Permission check results for application: "{application}" not found')


def get_structured_app(
    code: Optional[str] = None,
    uuid: Optional[UUID] = None,
    module_id: Optional[UUID] = None,
    env_id: Optional[int] = None,
    engine_app_id: Optional[UUID] = None,
) -> 'StructuredApp':
    """Get a structured application(with modules and envs) by various params

    :raise: ValueError when application can not be found
    """
    params = {
        'codes': [code],
        'uuids': [uuid],
        'module_id': module_id,
        'env_id': env_id,
        'engine_app_id': engine_app_id,
    }
    # Remove absent params
    params = {k: v for k, v in params.items() if v not in (None, [None])}
    if len(params.values()) != 1:
        raise ValueError('Must provide a single condition')

    data = get_local_plat_client().query_applications(**params)[0]  # type: ignore
    if not data:
        raise ValueError(f'Application conds={params!r} not found')
    return StructuredApp.from_json_data(data)


def get_env_by_engine_app_id(engine_app_id: UUID) -> 'ModuleEnv':
    """Get a module env object by engine app ID"""
    app = get_structured_app(engine_app_id=engine_app_id)
    return app.get_env_by_engine_app_id(engine_app_id)


def to_structured(application: Application) -> 'StructuredApp':
    """Make a structured application(with modules and envs) from a pure Application object

    :raise: ValueError when application can not be found
    """
    return get_structured_app(code=application.code)


@define
class StructuredApp:
    """A structured application model, contains extra info such as all module ids"""

    application: Application
    modules: List[Module] = Factory(list)
    module_envs: List[ModuleEnv] = Factory(list)

    @classmethod
    def from_json_data(cls, data: Dict) -> 'StructuredApp':
        """Create an object from json data"""
        app = cattr.structure(data['application'], Application)
        modules = [cattr.structure({'application': asdict(app), **m}, Module) for m in data['modules']]

        # Make a map to get module by id
        module_map = {str(m.id): m for m in modules}
        module_envs: List[ModuleEnv] = []
        for env in data['envs']:
            module = module_map[env['module_id']]
            module_envs.append(
                cattr.structure({'application': asdict(app), 'module': asdict(module), **env}, ModuleEnv)
            )
        return StructuredApp(application=app, modules=modules, module_envs=module_envs)

    @property
    def module_ids(self) -> List[UUID]:
        """All module's ids"""
        return [m.id for m in self.modules]

    def get_env_by_id(self, env_id: int) -> ModuleEnv:
        """Get a ModuleEnv object by id

        :raise: AppSubResourceNotFound when no result can be found
        """
        for env in self.module_envs:
            if env_id == env.id:
                return env
        raise AppSubResourceNotFound(f'environment_id={env_id}')

    def get_env_by_engine_app_id(self, engine_app_id: UUID) -> ModuleEnv:
        """Get a ModuleEnv object by engine app ID

        :raise: AppSubResourceNotFound when no result can be found
        """
        for env in self.module_envs:
            if engine_app_id == env.engine_app_id:
                return env
        raise AppSubResourceNotFound(f'engine_app_id={engine_app_id}')

    def get_envs_by_module(self, module: Module) -> List[ModuleEnv]:
        """Get ModuleEnv objects by module"""
        envs = []
        for env in self.module_envs:
            if env.module_id == module.id:
                envs.append(env)
        return envs

    def get_env_by_environment(self, module: Module, environment: str) -> ModuleEnv:
        """Get a ModuleEnv object by environment name("stag", "prod")

        :param module: environment's owner module
        :raise: AppSubResourceNotFound when no result can be found
        """
        for env in self.module_envs:
            if env.module_id == module.id and env.environment == environment:
                return env
        raise AppSubResourceNotFound(f'module={module.name} environment={environment}')

    def get_module_by_id(self, module_id: UUID) -> Module:
        """Get a Module object by id

        :raise: AppSubResourceNotFound when no result can be found
        """
        for module in self.modules:
            if str(module_id) == str(module.id):
                return module
        raise AppSubResourceNotFound(f'module_id={module_id}')

    def get_module_by_name(self, module_name: str) -> Module:
        """Get a Module object by name

        :raise: AppSubResourceNotFound when no result can be found
        """
        for module in self.modules:
            if module_name == module.name:
                return module
        raise AppSubResourceNotFound(f'module_name={module_name}')


class AppSubResourceDescriptor:
    """Base class for descriptor which provider app's sub-resource objects"""

    key_field: str = ''
    data_source_name = '_structured_app'

    def initialize(self, instance: object, conds: Dict) -> None:
        """Initialize structured data for givin instance

        :param conds: The condition for getting structured app
        """
        if not getattr(instance, self.key_field, None):
            raise ValueError(f'Attribute "{self.key_field}" not found on instance')

        try:
            instance.__dict__[self.data_source_name]
        except KeyError:
            # Retrieve structured application field once
            instance.__dict__[self.data_source_name] = get_structured_app(**conds)

    def __set__(self, instance, value):
        raise ValueError('set operation not allowed')


class ModuleAttrFromID(AppSubResourceDescriptor):
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
        self.initialize(instance, conds={'module_id': module_id})
        struct_app: StructuredApp = getattr(instance, self.data_source_name)
        return struct_app.get_module_by_id(module_id)


class ModuleEnvAttrFromID(AppSubResourceDescriptor):
    """A descriptor which make `{owner}.environment` available by reading from "_structured_app" property."""

    key_field = 'environment_id'

    @overload
    def __get__(self, instance: None, owner: None) -> 'ModuleEnvAttrFromID':
        ...

    @overload
    def __get__(self, instance: object, owner: Type) -> ModuleEnv:
        ...

    def __get__(self, instance, owner: Optional[Type] = None) -> Union['ModuleEnvAttrFromID', ModuleEnv]:
        """Read environment value

        :raise: ValueError when instance was not initialized with structured data
        :raise: AppSubResourceNotFound when no result can be found
        """
        if not instance:
            return self

        env_id = getattr(instance, self.key_field)
        self.initialize(instance, conds={'env_id': env_id})
        struct_app: StructuredApp = getattr(instance, self.data_source_name)
        return struct_app.get_env_by_id(env_id)


class ModuleEnvAttrFromName(AppSubResourceDescriptor):
    """A descriptor which make `{owner}.environment` available by reading from "_structured_app" property.

    - both `module_id` and `environment_name` fields are required.
    """

    key_field = 'environment_name'
    module_key_field = 'module_id'

    @overload
    def __get__(self, instance: None, owner: None) -> 'ModuleEnvAttrFromName':
        ...

    @overload
    def __get__(self, instance: object, owner: Type) -> ModuleEnv:
        ...

    def __get__(self, instance, owner: Optional[Type] = None) -> Union['ModuleEnvAttrFromName', ModuleEnv]:
        """Read environment value

        :raise: ValueError when instance was not initialized with structured data
        :raise: AppSubResourceNotFound when no result can be found
        """
        if not instance:
            return self

        module_id = getattr(instance, self.module_key_field)
        self.initialize(instance, conds={'module_id': module_id})
        struct_app: StructuredApp = getattr(instance, self.data_source_name)

        module = struct_app.get_module_by_id(module_id)
        env_name = getattr(instance, self.key_field)
        return struct_app.get_env_by_environment(module, env_name)


def set_model_structured(obj: object, application: Application):
    """Initialize an object with structured application data

    :param obj: Any valid data object which belongs to a single Application, multiple object supported
    :param application: The `Application` object which was used for initialization
    """
    data_source_name = AppSubResourceDescriptor.data_source_name
    if hasattr(obj, data_source_name):
        return
    setattr(obj, data_source_name, to_structured(application))


def set_many_model_structured(objs: Iterable[object], application: Application):
    """Initialize many objects with structured application data, the objs must
    share same application"""
    data_source_name = AppSubResourceDescriptor.data_source_name
    # Query for structured application only once
    struct_app = to_structured(application)
    for obj in objs:
        if hasattr(obj, data_source_name):
            return
        setattr(obj, data_source_name, struct_app)
