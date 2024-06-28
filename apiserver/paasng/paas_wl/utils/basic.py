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

import datetime
import hashlib
from collections import MutableMapping
from typing import Any, Collection, Dict
from uuid import UUID

import cattr
import requests
import requests.adapters
from blue_krill.cubing_case import shortcuts
from django.utils.encoding import force_bytes
from pydantic import ValidationError as PDValidationError
from pydantic.error_wrappers import display_errors

# Register cattr custom hooks
cattr.register_unstructure_hook(UUID, lambda val: str(val))  # type: ignore
cattr.register_structure_hook(UUID, lambda val, _: val if isinstance(val, UUID) else UUID(str(val)))
# End register


def get_time_delta(time_delta_string):
    """
    5m -> datetime.timedelta(minutes=5)
    5d -> datetime.timedelta(days=5)
    """
    count, _unit = time_delta_string[:-1], time_delta_string[-1]
    unit = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}.get(_unit, "minutes")
    return datetime.timedelta(**{unit: int(count)})


class AttrDict(MutableMapping):
    """Dict-like object that can be accessed by attributes"""

    def __init__(self, *args, **kwargs):
        self.__dict__.update(*args, **kwargs)

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def __setitem__(self, key, val):
        self.__setattr__(key, val)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)


def digest_if_length_exceeded(raw_str: str, limit: int):
    """如果字符串长度超长则将字符串摘要"""
    if len(raw_str) <= limit:
        return raw_str

    return hashlib.sha1(force_bytes(raw_str)).hexdigest()[:limit]


def make_subdict(d: Dict, allowed_keys: Collection):
    """Make a sub dict which includes only given keys

    :param d: original dict
    :param allowed_keys: a collections of keys
    :returns: A dict direivied from `d` but only contains `allowed_keys`
    """
    return {key: value for key, value in d.items() if key in allowed_keys}


# Make a global session object to turn on connection pooling
_requests_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
_requests_session.mount("http://", _adapter)
_requests_session.mount("https://", _adapter)


def get_requests_session() -> requests.Session:
    """Return the global requests session object which supports connection pooling"""
    return _requests_session


def convert_key_to_camel(data: Dict[str, Any]) -> Dict[str, Any]:
    """将字典中的所有下划线分隔的键转换为驼峰格式"""
    result: Dict[str, Any] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        camel_key = shortcuts.to_lower_camel_case(key)
        if isinstance(value, dict):
            result[camel_key] = convert_key_to_camel(value)
        elif isinstance(value, list):
            result[camel_key] = [convert_key_to_camel(item) if isinstance(item, dict) else item for item in value]
        else:
            result[camel_key] = value
    return result


def to_error_string(exc: PDValidationError) -> str:
    """Transform a pydantic Exception object to a one-line string"""
    # TODO: Improve error message format
    return display_errors(exc.errors()).replace("\n", " ")
