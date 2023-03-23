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
from typing import Any, Dict, Optional

from attrs import converters, define, field, fields

from paasng.platform.log.exceptions import LogLineInfoBrokenError
from paasng.platform.log.utils import NOT_SET, get_field_form_raw

logger = logging.getLogger(__name__)


def init_field_form_raw(self):
    for attr in fields(type(self)):
        if not attr.init:
            getter = attr.metadata.get(attr.name) or get_field_form_raw(attr.name)
            setattr(self, attr.name, getter(self.raw))
    for k, v in self.raw.items():
        if v is NOT_SET:
            self.raw[k] = None


@define
class StandardOutputLogLine:
    """标准输出日志结构"""

    timestamp: int
    message: str
    raw: Dict[str, Any]

    region: str = field(init=False, converter=converters.optional(str))
    app_code: str = field(init=False, converter=converters.optional(str))
    module_name: str = field(init=False, converter=converters.optional(str))
    environment: str = field(init=False, converter=converters.optional(str))
    process_id: str = field(init=False, converter=converters.optional(str))
    stream: str = field(init=False, converter=converters.optional(str))
    pod_name: str = field(init=False, converter=converters.optional(str))

    __attrs_post_init__ = init_field_form_raw


@define
class StructureLogLine:
    """结构化日志结构"""

    timestamp: int
    message: str
    raw: Dict[str, Any]

    region: str = field(init=False, converter=converters.optional(str))
    app_code: str = field(init=False, converter=converters.optional(str))
    module_name: str = field(init=False, converter=converters.optional(str))
    environment: str = field(init=False, converter=converters.optional(str))
    process_id: str = field(init=False, converter=converters.optional(str))
    stream: str = field(init=False, converter=converters.optional(str))

    __attrs_post_init__ = init_field_form_raw


def get_engine_app_name(raw_log: Dict):
    if "engine_app_name" not in raw_log:
        raise LogLineInfoBrokenError("engine_app_name")
    # ingress 日志是从 serviceName 解析的 engine_app_name，下划线已经转换成 0us0
    return raw_log["engine_app_name"].replace("0us0", "_")


@define
class IngressLogLine:
    """ingress 访问日志结构"""

    timestamp: int
    message: str
    raw: Dict

    engine_app_name: Optional[str] = field(
        init=False, converter=converters.optional(str), metadata={"getter": get_engine_app_name}
    )

    method: Optional[str] = field(init=False, converter=converters.optional(str))
    path: Optional[str] = field(init=False, converter=converters.optional(str))
    status_code: Optional[int] = field(init=False, converter=converters.optional(int))
    response_time: Optional[float] = field(init=False, converter=converters.optional(float))
    client_ip: Optional[str] = field(init=False, converter=converters.optional(str))
    bytes_sent: Optional[int] = field(init=False, converter=converters.optional(int))
    user_agent: Optional[str] = field(init=False, converter=converters.optional(str))
    http_version: Optional[str] = field(init=False, converter=converters.optional(str))

    __attrs_post_init__ = init_field_form_raw
