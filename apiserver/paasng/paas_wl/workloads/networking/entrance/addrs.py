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

"""Address related functionalities"""

from typing import NamedTuple, Optional
from urllib.parse import urlparse

from attrs import define

from paas_wl.infras.cluster.entities import PortMap
from paas_wl.workloads.networking.entrance.constants import AddressType

default_port_map = PortMap()


@define
class URL:
    protocol: str
    hostname: str
    port: int
    path: str
    query: str = ""

    def as_address(self):
        query = f"?{self.query}" if self.query else ""
        if default_port_map.get_port_num(self.protocol) == self.port:
            return f"{self.protocol}://{self.hostname}{self.path}{query}"
        else:
            return f"{self.protocol}://{self.hostname}:{self.port}{self.path}{query}"

    @classmethod
    def from_address(cls, address: str) -> "URL":
        parsed = urlparse(address)
        protocol = parsed.scheme or "http"
        port = parsed.port or default_port_map.get_port_num(protocol)
        assert parsed.hostname
        return URL(protocol=protocol, hostname=parsed.hostname, port=port, path=parsed.path, query=parsed.query)

    def compare_with(self, hostname: str, path: str) -> bool:
        """compare URL with `${hostname}${path}` pair"""
        # 判断域名和路径是否相同
        # 判断路径时去除两端的 "/", 避免根路径省略时无法正常匹配
        return self.hostname == hostname and self.path.strip("/") == path.strip("/")


class EnvExposedURL(NamedTuple):
    url: URL
    provider_type: str

    @property
    def address(self) -> str:
        return self.url.as_address()


@define
class Address:
    """Represents an exposed endpoint of application's deployed environments.

    :param type: Type of address
    :param url: URL, includes protocol and port number
    :param is_sys_reserved: Whether the address was generated from a reserved
        system domain
    :param id: id of the db object, only available for type=custom
    """

    type: AddressType
    url: str
    is_sys_reserved: bool = False
    id: Optional[str] = None

    def hostname_endswith(self, s: str) -> bool:
        """Check if current hostname ends with given string"""
        obj = URL.from_address(self.url)
        return obj.hostname.endswith(s)

    def to_exposed_url(self) -> EnvExposedURL:
        """To exposed URL object"""
        # INFO: Use self.type as "provider type" directly, this might need to be
        # changed in the future.
        return EnvExposedURL(url=URL.from_address(self.url), provider_type=self.type)
