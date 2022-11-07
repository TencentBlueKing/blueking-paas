# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from dataclasses import dataclass
from urllib.parse import urlparse

from paasng.engine.controller.models import PortMap

default_port_map = PortMap()


def to_dns_safe(s: str) -> str:
    """Tranform some string to dns safe"""
    return s.replace('_', '--').lower()


@dataclass
class URL:
    protocol: str
    hostname: str
    port: int
    path: str
    query: str = ''

    def as_address(self):
        query = f"?{self.query}" if self.query else ''
        if default_port_map.get_port_num(self.protocol) == self.port:
            return f"{self.protocol}://{self.hostname}{self.path}{query}"
        else:
            return f"{self.protocol}://{self.hostname}:{self.port}{self.path}{query}"

    @classmethod
    def from_address(cls, address: str) -> 'URL':
        parsed = urlparse(address)
        protocol = parsed.scheme or 'http'
        port = parsed.port or default_port_map.get_port_num(protocol)
        assert parsed.hostname
        return URL(protocol=protocol, hostname=parsed.hostname, port=port, path=parsed.path, query=parsed.query)
