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
from operator import attrgetter
from typing import Dict, List, Optional

from attrs import Factory, asdict, define
from cattr import register_structure_hook, structure_attrs_fromdict

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyCondType

logger = logging.getLogger(__name__)


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
    # https_enabled: 表示该域名是否打开 HTTPS 访问（要求提供对应证书）
    https_enabled: bool = False

    @staticmethod
    def structure(obj, cl):
        """对旧数据结构的兼容逻辑"""
        if isinstance(obj, str):
            return cl(name=obj)
        return structure_attrs_fromdict(obj, cl)


register_structure_hook(Domain, Domain.structure)


@define
class IngressConfig:
    # [保留选项] 一个默认的 Ingress 域名字符串模板，形如 "%s.example.com"。当该选项有值时，
    # 系统会为每个应用创建一个匹配域名 "{app_scheduler_name}.example.com" 的独一无二的 Ingress
    # 资源。配合其他负载均衡器，可完成复杂的请求转发逻辑。
    #
    # 该配置仅供特殊环境中使用，大部分情况下，请直接使用 app_root_domains 和 sub_path_domains。
    default_ingress_domain_tmpl: str = ""

    # 支持的子域名的根域列表, 在需要获取单个值的地方, 会优先使用第一个配置的根域名.
    app_root_domains: List[Domain] = Factory(list)
    # 支持的子路径的根域列表, 在需要获取单个值的地方, 会优先使用第一个配置的根域名.
    sub_path_domains: List[Domain] = Factory(list)
    # Ip address of frontend ingress controller
    frontend_ingress_ip: str = ""
    port_map: PortMap = Factory(PortMap)

    def __attrs_post_init__(self):
        self.app_root_domains = sorted(self.app_root_domains, key=attrgetter("reserved"))
        self.sub_path_domains = sorted(self.sub_path_domains, key=attrgetter("reserved"))

    def find_app_root_domain(self, hostname: str) -> Optional[Domain]:
        """Find the possible app_root_domain by given hostname"""
        for d in self.app_root_domains:
            if hostname.endswith(d.name):
                return d
        return None

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
class AllocationPolicy:
    """分配策略"""

    # 是否按环境分配
    env_specific: bool
    # 集群名称列表，非按环境分配时用
    clusters: List[str] | None = None
    # 环境 - 集群名称列表，按环境分配时用
    env_clusters: Dict[str, List[str]] | None = None

    def __attrs_post_init__(self):
        # 数据校验
        if self.env_specific:
            if not self.env_clusters:
                raise ValueError("env_clusters can not be empty when env_specific is True")
        elif not self.clusters:
            raise ValueError("clusters can not be empty when env_specific is False")

        # 清理无效数据
        if self.env_specific:
            self.clusters = None
        else:
            self.env_clusters = None


@define
class AllocationPrecedencePolicy:
    """分配策略（按规则）"""

    # 匹配规则（例：{"region_is": "default"}）
    matcher: Dict[ClusterAllocationPolicyCondType, str]
    # 具体的分配策略
    policy: AllocationPolicy
