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
"""Bk Svn server config helper utilities"""
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import urlparse

from paasng.platform.sourcectl.source_types import get_sourcectl_types


@dataclass
class BkSvnServerConfig:
    """Server config for Bk Svn"""

    base_url: str
    legacy_base_url: str
    su_name: str
    su_pass: str
    need_security: bool
    admin_url: str
    auth_mgr_cls: Optional[str] = None

    def get_base_path(self) -> str:
        return urlparse(self.base_url).path

    def get_admin_credentials(self) -> Dict[str, str]:
        return {
            "username": self.su_name,
            "password": self.su_pass,
        }

    def as_module_arguments(self, root_path: str) -> Dict:
        """Construct arguments with different `base_url` attribute with an extra path appended"""
        base_url = self.base_url + root_path
        return {
            "base_url": base_url,
            "username": self.su_name,
            "password": self.su_pass,
        }


def get_bksvn_config(region: str, name: Optional[str] = None) -> BkSvnServerConfig:
    """Get the config object of bk svn source controll type

    :param name: if given, will get spec type object by name, otherwise try to find the spec type object which was
        registered with type `BkSvnSourceTypeSpec` instead.
    :raise KeyError: name was given but no sourcectl type can be found
    :raise RuntimeError: No bk svn sourcectl type can be found
    """
    from paasng.platform.sourcectl.type_specs import BkSvnSourceTypeSpec

    sourcectl_types = get_sourcectl_types()
    if name:
        sourcectl_type = sourcectl_types.get(name)
        if not isinstance(sourcectl_type, BkSvnSourceTypeSpec):
            raise RuntimeError(f'Only bk_svn sourcectl type spec was supported, current type: {type(sourcectl_type)}')
    else:
        try:
            sourcectl_type = sourcectl_types.find_by_type(BkSvnSourceTypeSpec)
        except ValueError:
            raise RuntimeError(f'No sourcectl type spec can be found, region: {region}, name: {name}')

    # Return a default server config value when requested region was not configured,
    # which might happens when running mgrlegacy's unit tests
    return BkSvnServerConfig(**sourcectl_type.get_server_config(region, use_default_value=True))
