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

"""Utilities for project configs"""

import os
from typing import Any, Optional, Type

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.fields import get_attribute


class RegionAwareConfig:
    """A region aware config wrapper tool class

    :param user_settings: User settings, when it's a dict-like type and includes a key '_lookup_field' with value
        'region', current configs will be marked as region aware.
    """

    def __init__(self, user_settings: Any):
        try:
            lookup_field = user_settings["_lookup_field"]
        except (TypeError, KeyError):
            lookup_field = None

        if lookup_field == "region":
            self.lookup_with_region = True
            self.data = user_settings["data"]
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


def get_settings(django_settings_name: str, field_name: str, raise_if_missing=False, default=None):
    """Get a settings value, first in django settings, then find in Envs

    :param str django_settings_name: the settings name in django settings, the value must be a dict.
    :param str field_name: the setting name in settings.{django_settings_name}
    :param bool raise_if_missing: raise exception if settings was not set
    """
    if not hasattr(settings, django_settings_name):
        raise ImproperlyConfigured(f"Missing `{django_settings_name}` in settings.")

    def factory():
        config = getattr(settings, django_settings_name)
        if not isinstance(config, dict):
            raise ImproperlyConfigured(f"{django_settings_name} must be a dict!")

        try:
            return get_attribute(config, field_name.split("."))
        except ValueError:
            env_key = f"{django_settings_name}.{field_name}".replace(".", "_")
            value = os.getenv(env_key, default)
            if value is None and raise_if_missing:
                raise ImproperlyConfigured(f"Missing `{django_settings_name}.{field_name}` in settings.")
            return value

    return factory
