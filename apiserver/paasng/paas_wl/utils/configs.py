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
"""Utilities for project configs"""
from typing import Any, Optional, Type

from django.conf import settings


class RegionAwareConfig:
    """A region aware config wrapper tool class

    :param user_settings: User settings, when it's a dict-like type and includes a key '_lookup_field' with value
        'region', current configs will be marked as region aware.
    """

    def __init__(self, user_settings: Any):
        try:
            lookup_field = user_settings['_lookup_field']
        except (TypeError, KeyError):
            lookup_field = None

        if lookup_field == 'region':
            self.lookup_with_region = True
            self.data = user_settings['data']
        else:
            self.lookup_with_region = False
            self.data = user_settings

    def get(self, region: str, use_default_value: bool = False) -> Any:
        """Return the config value by region

        :param use_default_value: If True, when region was not found, it will return a default config instead
        """
        if not self.lookup_with_region:
            return self.data

        try:
            return self.data[region]
        except KeyError:
            if use_default_value:
                return next(iter(self.data.values()), {})
            raise

    def __bool__(self):
        return bool(self.data)


def get_region_aware(name: str, region: str, result_cls: Optional[Type] = None) -> Any:
    """Shortcut function for getting a region aware config from settings

    :param name: Name of settings
    :param region: Name of region
    :param result_cls: Optional, when given, will try initializing the config data with `data_cls`
    :raises: KeyError, when no config can be found for region
    """
    config = getattr(settings, name)
    result = RegionAwareConfig(config).get(region)
    if result_cls is not None:
        return result_cls(**result)
    else:
        return result
