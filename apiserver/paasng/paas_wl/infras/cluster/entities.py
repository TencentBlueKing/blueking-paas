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
from datetime import datetime
from operator import attrgetter
from typing import Any, Dict, List, Optional

from attrs import Factory, asdict, define
from cattr import register_structure_hook, structure_attrs_fromdict
from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.constants import ClusterAllocationPolicyCondType, HelmChartDeployStatus
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName

logger = logging.getLogger(__name__)


@define
class PortMap:
    """PortMap is used to declare the port of http/https protocol exposed by the ingress gateway."""

    http: int = 80
    https: int = 443
    grpc: int = settings.GRPC_PORT
    grpcs: int = settings.GRPC_PORT

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

    def get_domain_names(self) -> List[str]:
        """Get all domain names configured in this IngressConfig, including both "sub-domain"
        and "sub-path" domains.

        :return: A list of domain names
        """
        return [d.name for d in self.app_root_domains] + [d.name for d in self.sub_path_domains]

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

    def match(self, ctx: "AllocationContext") -> bool:
        # 匹配规则为空，则可以匹配所有
        if not self.matcher:
            return True

        # 按匹配规则检查，任意不匹配的，都直接返回 False
        for key, value in self.matcher.items():
            if key == ClusterAllocationPolicyCondType.REGION_IS:
                if ctx.region != value:
                    return False
            elif key == ClusterAllocationPolicyCondType.USERNAME_IN:
                usernames = [u.strip() for u in value.split(",")]
                if ctx.username not in usernames:
                    return False
            else:
                raise ValueError(f"unknown cluster allocation policy condition type: {key}")

        return True


@define
class AllocationContext:
    """集群分配上下文

    用于描述集群分配的上下文信息，包括租户 ID、可用区域、部署环境等。
    供集群分配器 ClusterAllocator 使用，建议优先使用 from_xxx 方法创建。

    :param tenant_id: 租户 ID
    :param region: 应用版本
    :param environment: 部署环境
    :param username: 操作人，非必选
    """

    tenant_id: str
    region: str
    environment: str
    username: str | None = None

    @classmethod
    def create_for_future_system_apps(cls):
        """Create a special context that is often used when the platform attempts to retrieve
        the cluster for an system application that has not been deployed.

        NOTE: The values used in this context are based on assumptions and past experiences,
        which could result in an incorrect cluster when the applications are deployed in the future.
        """
        tenant_id = OP_TYPE_TENANT_ID if settings.ENABLE_MULTI_TENANT_MODE else DEFAULT_TENANT_ID
        return cls(tenant_id=tenant_id, region=settings.DEFAULT_REGION_NAME, environment=AppEnvName.PROD.value)

    @classmethod
    def create_for_build_app(cls):
        """Create an allocation context for build smart app pod.

        NOTE: This context is used specifically for allocating cluster to run smart app builder pods.
        """
        tenant_id = OP_TYPE_TENANT_ID if settings.ENABLE_MULTI_TENANT_MODE else DEFAULT_TENANT_ID
        return cls(tenant_id=tenant_id, region=settings.DEFAULT_REGION_NAME, environment=AppEnvName.PROD.value)

    @classmethod
    def from_module_env(cls, module_env: ModuleEnvironment) -> "AllocationContext":
        return cls(
            tenant_id=module_env.application.tenant_id,
            region=module_env.application.region,
            environment=module_env.environment,
        )

    @classmethod
    def from_wl_app(cls, wl_app: "WlApp") -> "AllocationContext":
        return cls(
            tenant_id=wl_app.tenant_id,
            region=wl_app.region,
            environment=wl_app.environment,
        )

    def __str__(self):
        return (
            f"<tenant_id: {self.tenant_id}, region: {self.region}, "
            + f"env: {self.environment}, username: {self.username}>"
        )


@define
class AppImageRegistry:
    """应用镜像仓库"""

    host: str
    skip_tls_verify: bool
    namespace: str
    username: str
    password: str


@define
class DeployResult:
    # 部署状态
    status: HelmChartDeployStatus
    # 部署详情
    description: str
    # 部署时间
    created_at: datetime


@define
class HelmChart:
    # Chart 名称
    name: str
    # Chart 版本
    version: str
    # App 版本
    app_version: str
    # Chart 描述
    description: str


@define
class HelmRelease:
    # release 名称
    name: str
    # 部署的命名空间
    namespace: str
    # release 版本
    version: int
    # chart 信息
    chart: HelmChart
    # 部署信息
    deploy_result: DeployResult
    # 部署配置信息
    values: Dict
    # 部署的 k8s 资源信息
    resources: List[Dict[str, Any]]
    # 存储 release secret 名称
    secret_name: str
