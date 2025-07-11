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

from collections import UserList
from typing import Self

from attrs import define


@define
class EnvVariableObj:
    """A detailed env variable object with optional description."""

    key: str
    value: str
    description: str | None

    @classmethod
    def with_prefix(cls, prefix: str, key: str, value: str, description: str | None = None) -> Self:
        """Create an EnvVariableObj with a prefix."""
        return cls(key=prefix + key, value=value, description=description)


class EnvVariableList(UserList):
    """A list of EnvVariableObjs."""

    @property
    def map(self) -> dict[str, EnvVariableObj]:
        """Return a dictionary representation of the list, with keys as env variable names."""
        return {item.key: item for item in self}

    @property
    def kv_map(self) -> dict[str, str]:
        """Return a dictionary with env variable names as keys and their values as values."""
        return {item.key: item.value for item in self}
