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
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from paasng.engine.domains import CustomDomainService
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.models import Module
from paasng.publish.entrance.exposer import EnvExposedURL, get_addresses, get_exposed_url
from paasng.publish.entrance.utils import default_port_map
from paasng.publish.market.constant import ProductSourceUrlType
from paasng.publish.market.models import AvailableAddress, MarketConfig

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
        addrs = get_addresses(self.env)
        entrances = [a.to_exposed_url() for a in addrs]
        return [
            AvailableAddress(address=entrance.address, type=ProductSourceUrlType.ENGINE_PROD_ENV.value)
            for entrance in entrances
        ]

    @property
    def domain_addresses(self) -> List[AvailableAddress]:
        return [
            AvailableAddress(address=url.as_address(), type=ProductSourceUrlType.CUSTOM_DOMAIN.value)
            for url in CustomDomainService().list_urls(self.env)
        ]

    def filter_domain_address(self, address: str) -> Optional['AvailableAddress']:
        """获取与 `address` 完全匹配的 `MarketAvailableAddress` 对象"""
        o = urlparse(address)
        for available_address in self.domain_addresses:
            # 由于 独立域名 只记录了 hostname, 因此只匹配 hostname
            if available_address.hostname == o.hostname:
                return available_address
        return None


class ModuleEnvAvailableAddressHelper(AvailableAddressMixin):
    """模块访问地址 助手"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.module = self.env.module

    @property
    def addresses(self) -> List['AvailableAddress']:
        """模块环境中所有可选的访问入口"""
        return self.default_access_entrances + self.domain_addresses


@dataclass
class MarketAvailableAddressHelper(AvailableAddressMixin):
    """应用市场访问地址(主模块生产环境)助手"""

    market_config: MarketConfig

    def __post_init__(self):
        self.module = self.market_config.source_module
        if self.module.application.engine_enabled:
            self.env = self.module.get_envs("prod")

    @property
    def addresses(self) -> List['AvailableAddress']:
        """应用市场所有可选的访问入口"""
        if (
            not self.market_config.prefer_https
            and self.default_access_entrance.address
            and self.default_access_entrance.address == self.default_access_entrance_with_https.address
        ):
            # Return both HTTP and HTTPS options when current default address is
            # using HTTPS protocol.
            return [
                self.default_access_entrance_with_http,
                self.default_access_entrance_with_https,
            ] + self.domain_addresses

        return [self.default_access_entrance] + self.domain_addresses

    @property
    def default_access_entrance_with_http(self) -> AvailableAddress:
        """由平台提供的首选默认访问入口(HTTP协议)"""
        entrance = self.transform_entrance(get_exposed_url(self.env), protocol="http")
        return AvailableAddress(
            address=entrance.address if entrance else None,
            type=ProductSourceUrlType.ENGINE_PROD_ENV.value,
        )

    @property
    def default_access_entrance_with_https(self) -> AvailableAddress:
        """由平台提供的首选默认访问入口(HTTPS协议)"""
        entrance = self.transform_entrance(get_exposed_url(self.env), protocol="https")
        return AvailableAddress(
            address=entrance.address if entrance else None,
            type=ProductSourceUrlType.ENGINE_PROD_ENV_HTTPS.value,
        )

    @property
    def access_entrance(self) -> Optional[AvailableAddress]:
        """应用市场最终设置的主访问入口"""
        source_url_type = ProductSourceUrlType(self.market_config.source_url_type)

        if source_url_type == ProductSourceUrlType.ENGINE_PROD_ENV:
            if not self.market_config.prefer_https:
                return self.default_access_entrance_with_http
            return self.default_access_entrance
        elif source_url_type == ProductSourceUrlType.ENGINE_PROD_ENV_HTTPS:
            return self.default_access_entrance_with_https
        elif source_url_type == ProductSourceUrlType.CUSTOM_DOMAIN:
            return self.filter_domain_address(self.market_config.custom_domain_url)
        elif source_url_type == ProductSourceUrlType.THIRD_PARTY:
            return AvailableAddress(
                address=self.market_config.source_tp_url, type=ProductSourceUrlType.THIRD_PARTY.value
            )
        elif source_url_type == ProductSourceUrlType.DISABLED:
            return None
        raise NotImplementedError

    @staticmethod
    def transform_entrance(entrance: Optional[EnvExposedURL], protocol: str):
        if entrance and entrance.url.protocol != protocol:
            entrance.url.protocol = protocol
            entrance.url.port = default_port_map.get_port_num(protocol)
        return entrance
