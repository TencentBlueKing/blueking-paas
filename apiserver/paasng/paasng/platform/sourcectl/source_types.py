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

"""Sourcectl type specifications"""

import logging
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple, Type

import cattr
from blue_krill.data_types.enum import FeatureFlagField
from django.core.exceptions import ImproperlyConfigured
from django.test.signals import setting_changed
from django.utils.module_loading import import_string
from django.utils.translation import get_language
from pydantic import BaseModel, Field

from paasng.infras.accounts.oauth.backends import OAuth2Backend
from paasng.infras.accounts.oauth.utils import set_get_backends_callback_func
from paasng.platform.sourcectl.constants import DiffFeatureType
from paasng.utils.configs import get_settings
from paasng.utils.text import camel_to_snake, remove_suffix

if TYPE_CHECKING:
    from paasng.platform.sourcectl.connector import ModuleRepoConnector
    from paasng.platform.sourcectl.repo_controller import RepoController
    from paasng.platform.sourcectl.repo_provisioner import RepoProvisioner

logger = logging.getLogger(__name__)


class DisplayInfo(NamedTuple):
    """The sourcectl type information to be displayed on screen"""

    name: str
    value: str
    description: str


@dataclass
class DiffFeature:
    """describe diff feature of source type"""

    method: Optional[DiffFeatureType]
    enabled: bool = True

    def to_dict(self) -> dict:
        return {"method": self.method, "enabled": self.enabled}


class SourceTypeSpec:
    """Source type specifications"""

    # connector 是用于“连接”新应用模块与源码系统的类型，它的职责包含：完成绑定
    connector_class: Type["ModuleRepoConnector"]

    # 用来操作源码系统的功能类型，提供了导出项目源码、查看 diff 日志、下载代码、提交推送代码等能力
    repo_controller_class: Type["RepoController"]

    # 处理仓库供应和基础管理（创建仓库、初始化配置、成员权限等）的功能类型
    # 注意：与 repo_controller_class 不同，此类型操作不依赖具体仓库地址
    repo_provisioner_class: Optional[Type["RepoProvisioner"]] = None

    # 处理用户通过 OAuth 协议连接到外部 VCS 系统的后端类，部分源码系统（比如 GitHub、GitLab）适用，
    # 为空时表示当前源码系统不支持 OAuth 功能
    oauth_backend_class: Optional[Type["OAuth2Backend"]]

    diff_feature: DiffFeature = DiffFeature(method=DiffFeatureType.EXTERNAL, enabled=True)
    basic_type: str = ""

    _default_label: str = ""
    _default_display_info: Dict = {}

    def __init__(
        self,
        name: str,
        label: Optional[str] = None,
        display_info: Optional[Dict] = None,
        enabled: bool = False,
        server_config: Optional[Dict] = None,
        oauth_backend_config: Optional[Dict] = None,
        oauth_credentials: Optional[Dict] = None,
    ):
        """Source type specs object.

        :param name: The name of source type, it's upper case will be used for feature flag and enum
        :param label: Optional, enum label name
        :param display_info: Optional, info used for displaying current system on UI
        :param enabled: Whether this system was enabled, will affect the related FeatureFlag value
        :param server_config: The server config information
        :param oauth_backend_config: The credential settings(optionally, and display_info) for OAuth authentication
        :param oauth_credentials: [Deprecated] The credential settings for OAuth authentication,
                                  please use oauth_backend_config instead.
        """
        self.name = name
        self.upper_name = name.upper()

        self.label = label or self._default_label
        self.display_info = DisplayInfo(value=self.name, **(display_info or self._default_display_info))
        self.enabled = enabled
        self.server_config = server_config or {}
        self.oauth_backend_config = oauth_backend_config or {}
        if oauth_credentials:
            logger.warning("The 'oauth_credentials' will be removed in the next version.")
            self.oauth_backend_config.update(oauth_credentials)

    def support_oauth(self) -> bool:
        """Check if current source type supports oauth backend"""
        return bool(self.oauth_backend_class)

    def make_oauth_backend(self) -> "OAuth2Backend":
        if self.oauth_backend_class:
            return cattr.structure(self.oauth_backend_config, self.oauth_backend_class)
        raise NotImplementedError

    def get_server_config(self) -> Dict:
        """Get configured server config data"""
        return self.server_config

    def config_as_arguments(self) -> Dict:
        """
        Make source type related class and function arguments from server config,
        the result might be used for Connector and Controller class's initialization
        """
        return self.get_server_config()

    def make_feature_flag_field(self) -> FeatureFlagField:
        feature = f"ENABLE_{self.upper_name}"
        return FeatureFlagField(name=feature, label=f"使用 {self.label} 源码服务", default=self.enabled)


class SourceTypes:
    """Stores source types"""

    def __init__(self):
        self.data = OrderedDict()
        self.initialized = False
        self.names = SourcectlTypeNames(self)

    def items(self) -> Iterable[Tuple[str, SourceTypeSpec]]:
        """Return all content"""
        return self.data.items()

    def get_choices(self) -> List[Tuple[str, str]]:
        """Get current types as choices tuple"""
        return [(type_.name, type_.label) for type_ in self.data.values()]

    def get_choice_label(self, name: str) -> str:
        """Get label value by sourcectl name

        :param name: name of sourcectl type spec
        :returns: label string
        """
        return self.get(name).label

    def get(self, name: str) -> SourceTypeSpec:
        """Get source type specs by it's name

        :raises KeyError: when nothing can be found
        """
        for key, type_spec in self.data.items():
            if key.upper() == name.upper():
                return type_spec
        raise KeyError(f"{name} is not a valid source type value")

    def search(self, key: str) -> SourceTypeSpec:
        """Call `self.names.get` API to search sourcectl type"""
        name = self.names.get(key)
        return self.get(name)

    def find_by_type(self, spec_type: Type[SourceTypeSpec]) -> SourceTypeSpec:
        """Find a source spec by type class"""
        for spec in self.data.values():
            if isinstance(spec, spec_type):
                return spec
        raise ValueError(f"{spec_type} not exists in source_types")

    def clear(self):
        """Remove all sourcectl type specs"""
        self.data.clear()

    def load_from_configs(self, configs: List):
        """Register source types from settings"""
        from .constants import register_new_sourcectl_type

        for conf in configs:
            # Make source type specs and store it into current source types
            cls = import_string(conf["spec_cls"])
            type_specs = cls(**conf["attrs"])
            self.data[type_specs.name] = type_specs

            register_new_sourcectl_type(type_specs.make_feature_flag_field())

        self.initialized = True


class SourcectlTypeNames:
    """Source type "NAME" helper class"""

    common_spec_type_suffix = "SourceTypeSpec"

    def __init__(self, source_types: SourceTypes):
        self.types = source_types

    def get(self, key: str) -> str:
        """Get the sourcectl type name by keyword. For example, if the source type was registered via
        type `BkSvnSourceTypeSpec`, it's name can be queried by below keywords:

        - {name}: by name itself
        - 'BkSvnSourceTypeSpec': the full name of spec type
        - 'BkSvn': the name with 'SourceTypeSpec' suffix removed
        - 'bk_svn': shorter type name lower cased

        The matching priority decreases.

        :raises: KeyError when no sourcectl type can be found via given keyword or multiple names were found
        """
        # Build index every time, this behaviour can be improved by introducing a cache
        indices = [
            self._build_name_index(),
            self._build_type_name_index(),
            self._build_shorter_type_name_index(),
        ]
        results = None
        for index in indices:
            try:
                results = index[key]
                if results:
                    break
            except KeyError:
                continue

        if not results:
            raise KeyError(f"No sourcectl type name can be found by {key}")
        if len(results) > 1:
            raise KeyError(f"Multiple names were found by {key}")
        return results[0]

    def get_default(self) -> str:
        """Return the default sourcectl type name"""
        return next(iter(self.types.data.keys()), "")

    def filter_by_basic_type(self, basic_type: str) -> Sequence[str]:
        """Filter names by basic_type attr"""
        results = []
        for name, spec in self.types.items():
            if spec.basic_type == basic_type:
                results.append(name)
        return results

    def validate_svn(self, name: str) -> bool:
        return name in self.filter_by_basic_type("svn")

    def validate_git(self, name: str) -> bool:
        return name in self.filter_by_basic_type("git")

    def __getattr__(self, name: str) -> str:
        """Shortcut API for `get` method"""
        return self.get(key=name)

    def _build_name_index(self) -> Dict[str, List[str]]:
        """Build index by full name"""
        return {name: [name] for name, _ in self.types.items()}

    def _build_type_name_index(self) -> Dict[str, List[str]]:
        """Build index by type spec class name"""
        result = defaultdict(list)
        for name, sourcectl_type in self.types.items():
            key = sourcectl_type.__class__.__name__
            result[key].append(name)
        return result

    def _build_shorter_type_name_index(self) -> Dict[str, List[str]]:
        """Build index by shorter type spec class name"""
        result = defaultdict(list)
        for name, sourcectl_type in self.types.items():
            key = sourcectl_type.__class__.__name__
            short_key = remove_suffix(key, self.common_spec_type_suffix)

            # Store both camel and snake cases of short name
            result[short_key].append(name)
            result[camel_to_snake(short_key)].append(name)
        return result


class DockerRegistryConf(BaseModel):
    default_registry: str = Field(default_factory=get_settings("DOCKER_REGISTRY_CONFIG", "DEFAULT_REGISTRY"))
    allow_third_party_registry: bool = Field(
        default_factory=get_settings("DOCKER_REGISTRY_CONFIG", "ALLOW_THIRD_PARTY_REGISTRY", default=False)
    )

    def reload(self):
        for field_name, field in self.__fields__.items():
            if field.default_factory:
                setattr(self, field_name, field.default_factory())


_current_source_types_map: Dict[str, SourceTypes] = {}


def get_sourcectl_types() -> SourceTypes:
    """Get current sourcectl types object"""
    from paasng.platform.sourcectl.models import SourceTypeSpecConfig

    lang = get_language()
    # 若当前语言，存在已经初始化的 source_types 则直接返回
    source_types = _current_source_types_map.get(lang, SourceTypes())
    if source_types.initialized:
        return source_types

    # 不存在的语言版本，则进行初始化，并存储到内存缓存中
    configs = SourceTypeSpecConfig.objects.build_configs()
    if not configs:
        raise ImproperlyConfigured("You have to configure at least one source control system")

    source_types.load_from_configs(configs)
    _current_source_types_map[lang] = source_types
    return source_types


def refresh_sourcectl_types(source_type_configs: List):
    """Refresh current sourcectl types with given user settings"""
    if not _current_source_types_map:
        _current_source_types_map[get_language()] = SourceTypes()

    for source_types in _current_source_types_map.values():
        source_types.clear()
        source_types.load_from_configs(source_type_configs)


def get_sourcectl_type(name: str) -> SourceTypeSpec:
    """Get source control type spec by name"""
    return get_sourcectl_types().get(name)


def get_sourcectl_names():
    """Get current sourcectl types names helper object"""
    return get_sourcectl_types().names


docker_registry_config = DockerRegistryConf()


def reload_settings(setting, value, enter, *args, **kwargs):
    """listen the signal for override_settings, and reload the settings."""
    if setting == "DOCKER_REGISTRY_CONFIG":
        docker_registry_config.reload()


setting_changed.connect(reload_settings)


# Connect with the oauth2 lib


def list_oauth_backends() -> List[Tuple[str, OAuth2Backend]]:
    """Return the oauth backends by the current source type specs"""
    items = []
    for name, type_spec in get_sourcectl_types().items():
        if type_spec.support_oauth():
            items.append((name, type_spec.make_oauth_backend()))
    return items


# Set the callback function
set_get_backends_callback_func(list_oauth_backends)
