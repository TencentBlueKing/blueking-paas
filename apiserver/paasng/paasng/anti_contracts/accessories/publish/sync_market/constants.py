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

"""
被 paasng/infras/legacydb_te/adaptors.py 引用
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class EnvItem:
    key: str
    value: str
    description: str
    is_builtin: bool
    environment_name: Optional[str] = None


class RegionConverter:
    _data = {
        "ieod": "ied",
    }
    _data_reverse = {v: k for k, v in list(_data.items())}

    @classmethod
    def to_old(cls, region):
        return cls._data.get(region, region)

    @classmethod
    def to_new(cls, region):
        return cls._data_reverse.get(region, region)
