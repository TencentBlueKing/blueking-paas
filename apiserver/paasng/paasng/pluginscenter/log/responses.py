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
from typing import Dict, Optional

from attrs import converters, define, field, fields


@define
class StandardOutputLogLine:
    """标准输出日志结构"""

    timestamp: int
    message: str


@define
class StructureLogLine:
    """结构化日志结构"""

    timestamp: int
    message: str
    raw: Dict


@define
class IngressLogLine:
    """ingress 访问日志结构"""

    timestamp: int
    message: str
    raw: Dict

    method: Optional[str] = field(init=False, converter=converters.optional(str))
    path: Optional[str] = field(init=False, converter=converters.optional(str))
    status_code: Optional[int] = field(init=False, converter=converters.optional(int))
    response_time: Optional[float] = field(init=False, converter=converters.optional(float))
    client_ip: Optional[str] = field(init=False, converter=converters.optional(str))
    bytes_sent: Optional[int] = field(init=False, converter=converters.optional(int))
    user_agent: Optional[str] = field(init=False, converter=converters.optional(str))
    http_version: Optional[str] = field(init=False, converter=converters.optional(str))

    def __attrs_post_init__(self):
        for attr in fields(type(self)):
            if not attr.init:
                setattr(self, attr.name, self.raw.get(attr.name))
