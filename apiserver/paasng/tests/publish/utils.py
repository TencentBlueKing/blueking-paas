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
import itertools
from typing import Dict, List, Optional

from paasng.publish.entrance.exposer import Address


class ModuleLiveAddrs:
    """Stored a module's addresses and running status"""

    default_addr_type_ordering = ['subpath', 'subdomain', 'custom']

    def __init__(self, data: List[Dict]):
        self._data = data
        self._map_by_env = {}
        for item in data:
            self._map_by_env[item['env']] = item

    def get_is_running(self, env_name: str) -> bool:
        """Given running status of environment"""
        d = self._map_by_env.get(env_name, self._empty_item)
        return d['is_running']

    def get_addresses(self, env_name: str, addr_type: Optional[str] = None) -> List[Address]:
        """Return addresses of environment, the result was sorted, shorter and
        not reserved addresses are in front.

        :param addr_type: If given, include items whose type equal to this value
        """
        d = self._map_by_env.get(env_name, self._empty_item)
        addrs = d['addresses']
        if addr_type:
            addrs = [a for a in d['addresses'] if a['type'] == addr_type]
        items = [Address(**a) for a in addrs]
        self._sort_addrs(items)
        return items

    def get_all_addresses(self, addr_type: Optional[str] = None) -> List[Address]:
        """Return all addresses despite environment and running status

        :param addr_type: If given, include items whose type equal to this value
        """
        addrs = list(itertools.chain(*[d['addresses'] for d in self._map_by_env.values()]))
        if addr_type:
            addrs = [a for a in addrs if a['type'] == addr_type]
        items = [Address(**a) for a in addrs]
        self._sort_addrs(items)
        return items

    @classmethod
    def _sort_addrs(cls, items: List[Address]):
        """Sort a list of address objects"""
        # Make a map for sorting
        addr_type_ordering_map = {}
        for i, val in enumerate(cls.default_addr_type_ordering):
            addr_type_ordering_map[val] = i

        # Sort the addresses by below factors:
        # - type in the order of `default_addr_type_ordering`
        # - not reserved first
        # - shorter URL first
        items.sort(
            key=lambda addr: (
                addr_type_ordering_map.get(addr.type, float('inf')),
                addr.is_sys_reserved,
                len(addr.url),
            )
        )
        return items

    @property
    def _empty_item(self) -> Dict:
        """An empty item for handling default cases"""
        return {'is_running': False, 'addresses': []}
