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

import logging
from dataclasses import dataclass
from typing import List, Optional

from paas_wl.workloads.networking.entrance.addrs import EnvExposedURL, default_port_map
from paas_wl.workloads.networking.entrance.shim import LiveEnvAddresses, get_builtin_addrs
from paasng.accessories.publish.entrance.exposer import get_exposed_url
from paasng.accessories.publish.market.constant import ProductSourceUrlType
from paasng.accessories.publish.market.models import AvailableAddress, MarketConfig
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class AvailableAddressMixin:
    module: Module
    env: ModuleEnvironment

    @property
    def default_access_entrance(self) -> AvailableAddress:
        """由平台提供的首选默认访问入口"""
        entrance = get_exposed_url(self.env)
        return AvailableAddress(
            address=entrance.address if entrance else None,
            type=ProductSourceUrlType.ENGINE_PROD_ENV.value,
        )

    @property
    def default_access_entrances(self) -> List[AvailableAddress]:
        """由平台提供的所有默认访问入口"""
        _, addresses = get_builtin_addrs(self.env)
        return [
            AvailableAddress(address=addr.url, type=ProductSourceUrlType.ENGINE_PROD_ENV.value) for addr in addresses
        ]

    @property
    def domain_addresses(self) -> List[AvailableAddress]:
        return [
            AvailableAddress(address=addr.url, type=ProductSourceUrlType.CUSTOM_DOMAIN.value)
            for addr in LiveEnvAddresses(self.env).list_custom()
        ]

    def filter_domain_address(self, address: str) -> Optional["AvailableAddress"]:
        """获取与 `address` 完全匹配的 `MarketAvailableAddress` 对象"""
        for available_address in self.domain_addresses:
            if available_address.address == address:
                return available_address
        return None


class ModuleEnvAvailableAddressHelper(AvailableAddressMixin):
    """模块访问地址 助手"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.module = self.env.module

    @property
    def addresses(self) -> List["AvailableAddress"]:
        """模块环境中所有可选的访问入口"""
        return self.default_access_entrances + self.domain_addresses


@dataclass
class MarketAvailableAddressHelper(AvailableAddressMixin):
    """应用市场访问地址(绑定模块的生产环境)助手"""

    market_config: MarketConfig

    def __post_init__(self):
        self.module = self.market_config.source_module
        if self.module.application.engine_enabled:
            self.env = self.module.get_envs("prod")

    @property
    def default_access_entrance_with_http(self) -> AvailableAddress:
        """由平台提供的首选默认访问入口(HTTP协议)"""
        entrance = self.transform_protocol(get_exposed_url(self.env), protocol="http")
        return AvailableAddress(
            address=entrance.url.as_address() if entrance else None,
            type=ProductSourceUrlType.ENGINE_PROD_ENV.value,
        )

    @property
    def access_entrance(self) -> Optional[AvailableAddress]:
        """应用市场最终设置的主访问入口"""
        source_url_type = ProductSourceUrlType(self.market_config.source_url_type)

        if source_url_type == ProductSourceUrlType.ENGINE_PROD_ENV:
            if self.market_config.prefer_https is False:
                return self.default_access_entrance_with_http
            return self.default_access_entrance
        elif source_url_type == ProductSourceUrlType.ENGINE_PROD_ENV_HTTPS:
            return self.default_access_entrance
        # 自定义地址，不验证是否为主模块的自定义地址，否则会导致切换主模块后应用市场地址为 None
        elif source_url_type == ProductSourceUrlType.CUSTOM_DOMAIN:
            return self.market_config.custom_domain_url
        elif source_url_type == ProductSourceUrlType.THIRD_PARTY:
            return AvailableAddress(
                address=self.market_config.source_tp_url, type=ProductSourceUrlType.THIRD_PARTY.value
            )
        elif source_url_type == ProductSourceUrlType.DISABLED:
            return None
        raise NotImplementedError

    @staticmethod
    def transform_protocol(entrance: Optional[EnvExposedURL], protocol: str) -> Optional[EnvExposedURL]:
        if not entrance or protocol == entrance.url.protocol:
            return entrance
        entrance.url.protocol = protocol
        entrance.url.port = default_port_map.get_port_num(protocol)
        return entrance
