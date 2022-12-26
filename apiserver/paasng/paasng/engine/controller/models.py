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
from operator import attrgetter
from typing import List, Optional

from attrs import Factory, asdict, define

from paasng.engine.constants import ClusterType


@define
class PortMap:
    """PortMap is used to declare the port of http/https protocol exposed by the ingress gateway."""

    http: int = 80
    https: int = 443

    def get_port_num(self, protocol: str) -> int:
        """Return port number by protocol"""
        return asdict(self)[protocol]


@define
class Domain:
    name: str
    # reserved: 表示该域名是否保留域名
    reserved: bool = False
    # https_enabled: 表示该域名是否支持 https
    https_enabled: bool = False


@define
class IngressConfig:
    # 支持的子域名的根域列表, 在需要获取单个值的地方, 会优先使用第一个配置的根域名.
    app_root_domains: List[Domain] = Factory(list)
    # 支持的子路径的根域列表, 在需要获取单个值的地方, 会优先使用第一个配置的根域名.
    sub_path_domains: List[Domain] = Factory(list)
    # Ip address of frontend ingress controller
    frontend_ingress_ip: str = ''
    port_map: PortMap = Factory(PortMap)

    def __attrs_post_init__(self):
        self.app_root_domains = sorted(self.app_root_domains, key=attrgetter("reserved"))
        self.sub_path_domains = sorted(self.sub_path_domains, key=attrgetter("reserved"))

    def find_subdomain_domain(self, host: str) -> Optional[Domain]:
        """Find domain object in configured sub-domains by given host.

        :param host: Any valid host name
        """
        for d in self.app_root_domains:
            if d.name == host:
                return d
        return None

    def find_subpath_domain(self, host: str) -> Optional[Domain]:
        """Find domain object in configured sub-path domains by given host.

        :param host: Any valid host name
        """
        for d in self.sub_path_domains:
            if d.name == host:
                return d
        return None

    @property
    def default_root_domain(self) -> Domain:
        return self.app_root_domains[0]

    @property
    def default_sub_path_domain(self) -> Domain:
        return self.sub_path_domains[0]


@define
class ClusterFeatureFlags:
    enable_egress_ip: bool = False
    enable_mount_log_to_host: bool = False
    ingress_user_pattern: bool = False


@define
class Cluster:
    name: str
    is_default: bool
    ingress_config: IngressConfig = Factory(IngressConfig)
    # BCS 所属集群, 用于前端展示
    bcs_cluster_id: str = ""
    type: str = ClusterType.NORMAL
    # 集群特性（一般与集群类型相关）
    feature_flags: ClusterFeatureFlags = Factory(ClusterFeatureFlags)
