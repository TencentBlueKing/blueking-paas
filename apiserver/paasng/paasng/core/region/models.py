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
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Set

from django.conf import settings

from .exceptions import RegionDoesNotExists, RegionDuplicated

__all_regions: "OrderedDict[str, Region]" = OrderedDict()


def get_all_regions() -> Dict[str, "Region"]:
    return __all_regions


def filter_region_by_name(name_list):
    region_list = []
    for name in name_list:
        region_list.append(get_region(name))
    return region_list


def register_region(region: "Region"):
    """Registry a new region"""
    __all_regions[region.name] = region


def get_region(name: str):
    """Get the region class by region name
    :param str name: region name, such as 'ieod'
    """
    return get_all_regions()[name]


class RegionList(list):
    def __str__(self):
        return str(";".join([x.name for x in self]))

    def has_region_by_name(self, region_name):
        try:
            self.get_region_by_name(region_name)
        except Exception:
            return False
        else:
            return True

    def get_region_by_name(self, region_name):
        regions = [x for x in self if x.name == region_name]
        if len(regions) > 1:
            raise RegionDuplicated("Region request more than 1")
        elif len(regions) == 0:
            raise RegionDoesNotExists("Region request does not exist")

        return regions[0]


class RegionBasicInfo:
    """Basic info for region

    :param str description: description for this region
    :param str link_engine_app: visit link for engine_app
    :param str link_production_app: visit link for app production env
    :param dict built_in_config_var: built-in config variables in this region
    """

    def __init__(
        self,
        description,
        link_engine_app,
        link_production_app,
        extra_logo_bucket_info,
        deploy_ver_for_update_svn_account,
        legacy_deploy_version,
        built_in_config_var,
    ):
        self.description = description
        self.link_engine_app = link_engine_app
        self.link_production_app = link_production_app
        self.extra_logo_bucket_info = extra_logo_bucket_info
        self.deploy_ver_for_update_svn_account = deploy_ver_for_update_svn_account
        self.legacy_deploy_version = legacy_deploy_version
        self.built_in_config_var = built_in_config_var

    def get_extra_logo_bucket_name(self):
        return self.extra_logo_bucket_info["name"] if self.extra_logo_bucket_info else None

    @staticmethod
    def get_logo_bucket_name():
        return settings.APP_LOGO_BUCKET


class RegionMobileConfig:
    def __init__(self, enabled=False, etcd_servers=None, **kwargs):
        self.enabled = enabled
        self.etcd_servers = etcd_servers
        for k, v in list(kwargs.items()):
            if not k.endswith("_prefix"):
                raise ValueError("__init__ takes exactly 1 argument {}".format(k))
            setattr(self, k, v)


@dataclass
class RegionEntranceConfig:
    exposed_url_type: str
    manually_upgrade_to_subdomain_allowed: bool
    app_subpath_shared_domain: str = field(default="[deprecated]")


@dataclass
class RegionMulModulesConfig:
    creation_allowed: bool


class SvcCategoriesLoader(Protocol):
    """The loader for loading service categories"""

    def __call__(self, region: str) -> List:
        ...


# The loader function that loads service categories, set it when all modules are initialized.
_service_categories_loader: Optional[SvcCategoriesLoader] = None


def set_service_categories_loader(loader: SvcCategoriesLoader):
    global _service_categories_loader
    _service_categories_loader = loader


@dataclass
class Region:
    """Region represents a region in current PaaS platform, it will be used for:

    - Filter and sort services categories
    - Customize App Creation options, such as `supported languages` etc.
    """

    name: str
    display_name: str
    basic_info: RegionBasicInfo
    entrance_config: RegionEntranceConfig
    mul_modules_config: RegionMulModulesConfig
    enabled_feature_flags: Set[str] = field(default_factory=set)
    module_mobile_config: Optional[RegionMobileConfig] = None
    provide_env_vars_platform: Optional[bool] = True
    allow_deploy_app_by_lesscode: Optional[bool] = False

    def __post_init__(self):
        self._service_categories = []

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(repr(self))

    @property
    def service_categories(self):
        return self._service_categories

    def load_dynamic_infos(self):
        if not _service_categories_loader:
            raise RuntimeError("the svc categories loader is not found")

        self._service_categories = _service_categories_loader(self.name)

    def get_built_in_config_var(self, key, env):
        return self.basic_info.built_in_config_var.get(key, {}).get(env, "")
