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
import logging
from typing import TYPE_CHECKING, Optional

import cattr
from attrs import define

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import WlApp

logger = logging.getLogger(__name__)


@define
class WlAppMetadata:
    """An engine app's metadata object, contains essential information"""

    paas_app_code: str = ''  # Owner application's code
    module_name: str = ''  # Owner module's name
    environment: str = ''  # Bound environment name
    bkpa_site_id: Optional[int] = None  # Site ID for "PaaS Analysis" service
    acl_is_enabled: bool = False  # Whether ACL module is enabled
    mapper_version: str = ''  # mapper_version of the k8s resources naming rules

    def get_paas_app_code(self) -> str:
        """Get "paas_app_code" property, raise `RuntimeError` if result is empty, which
        means the source data might be corrupted.
        """
        if not self.paas_app_code:
            raise RuntimeError('"paas_app_code" is empty')
        return self.paas_app_code


def get_metadata(wl_app: 'WlApp') -> WlAppMetadata:
    """Get metadata object"""
    # TODO: Use `make_json_field()` to get structured object from Model directly
    json_data = wl_app.latest_config.metadata or {}
    return cattr.structure(json_data, WlAppMetadata)


def update_metadata(wl_app: 'WlApp', **kwargs) -> None:
    """Update wl_app's metadata by key, only valid keys(see `WlAppMetadata`) are allowed

    :param kwargs: New metadata values
    """
    latest_config = wl_app.latest_config
    obj = cattr.structure(latest_config.metadata or {}, WlAppMetadata)

    for key, value in kwargs.items():
        # If given key is not a valid attribute of WlAppMetadata type, raise error
        if not hasattr(obj, key):
            raise ValueError(f'{key} is invalid')
        setattr(obj, key, value)

    latest_config.metadata = cattr.unstructure(obj)
    latest_config.save(update_fields=['metadata', 'updated'])
