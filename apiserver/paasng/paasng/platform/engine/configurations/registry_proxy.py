# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""构建镜像代理：集群开关开启后，构建容器只持有构建 token，经镜像代理访问平台仓库"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

from paas_wl.infras.cluster.constants import ClusterAnnotationKey
from paas_wl.infras.cluster.utils import get_cluster_by_app, get_image_registry_by_app
from paasng.platform.engine.configurations.build_token import (
    BuildTokenUnavailable,
    load_active_signing_key,
    make_upstream_alias,
)

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.entities import BuildMetadata
    from paas_wl.bk_app.applications.models import WlApp

# 构建容器访问代理时使用的用户名，代理只读取密码段（即构建 token）
BUILD_TOKEN_USERNAME = "bkpaas-build"


@dataclass(frozen=True)
class BuildRegistryProxy:
    """本次构建使用的镜像代理

    :param address: 代理地址，构建环境中所有出现代理地址的位置都必须与其一致
    :param skip_tls_verify: 是否跳过代理证书校验
    :param registry_host: 平台仓库主机
    :param upstream_alias: 平台仓库在代理中的上游别名
    """

    address: str
    skip_tls_verify: bool
    registry_host: str
    upstream_alias: str

    @property
    def upstream_prefix(self) -> str:
        """平台仓库在代理下的路径前缀：<代理地址>/<上游别名>"""
        return f"{self.address}/{self.upstream_alias}"

    @property
    def registry_map(self) -> str:
        """kaniko `--registry-map` 的一项：<平台仓库主机>=<代理地址>/<上游别名>"""
        return f"{self.registry_host}={self.upstream_prefix}"

    def rewrite(self, reference: str) -> str:
        """把平台仓库中的镜像引用改写为经代理访问的地址，例如 `H/ns/app:tag` -> `P/<别名>/ns/app:tag`

        :raises BuildTokenUnavailable: 镜像引用不在平台仓库中
        """
        host_prefix = f"{self.registry_host}/"
        if not reference.startswith(host_prefix):
            raise BuildTokenUnavailable(f"image {reference} does not belong to the platform image registry")
        return f"{self.upstream_prefix}/{reference.removeprefix(host_prefix)}"


def get_build_registry_proxy(wl_app: "WlApp", metadata: "BuildMetadata") -> BuildRegistryProxy | None:
    """获取本次构建使用的镜像代理，构建不经代理时返回 None。目前仅 Dockerfile 构建接入代理

    集群开关开启时检查开启前置条件，任一不满足都必须让构建直接失败，不得回退为注入真实凭证。

    :raises BuildTokenUnavailable: 集群开关已开启，但开启前置条件不满足
    """
    # 目前只有 Dockerfile（kaniko）构建接入代理，其他构建方式保持原环境变量
    if not metadata.use_dockerfile:
        return None

    annos = get_cluster_by_app(wl_app).annotations
    # 开关关闭时环境变量必须与改造前一致
    if not is_build_registry_proxy_enabled(annos):
        return None

    # 产物路径和上游别名都由平台仓库的 host、namespace 生成
    registry = get_image_registry_by_app(wl_app)
    if not registry.host or not registry.namespace:
        raise BuildTokenUnavailable("platform image registry host or namespace is empty")
    return make_build_registry_proxy(annos, registry.host)


def is_build_registry_proxy_enabled(cluster_annotations: Mapping[str, str]) -> bool:
    """构建所在集群是否开启了镜像代理开关"""
    return cluster_annotations.get(ClusterAnnotationKey.ENABLE_BUILD_REGISTRY_PROXY) == "true"


def make_build_registry_proxy(cluster_annotations: Mapping[str, str], registry_host: str) -> BuildRegistryProxy:
    """集群开关已开启时，检查开启前置条件并返回本次构建使用的镜像代理

    :param cluster_annotations: 构建所在集群的注解
    :param registry_host: 本次构建产物所在的平台仓库主机
    :raises BuildTokenUnavailable: 开启前置条件不满足
    """
    # 开关已开启就不能回退为注入平台凭证。没有代理地址就无法改写镜像引用和凭证键
    address = cluster_annotations.get(ClusterAnnotationKey.BUILD_REGISTRY_PROXY_ADDRESS)
    if not address:
        raise BuildTokenUnavailable("build registry proxy address is not configured")

    # 主机带协议或为 IPv6 字面量时无法得到合法别名，也就无法生成 P/<别名>/... 这种路径
    try:
        alias = make_upstream_alias(registry_host)
    except ValueError:
        raise BuildTokenUnavailable(
            f"cannot derive an upstream alias from the platform image registry host: {registry_host}"
        ) from None
    # 代理地址与平台仓库主机相同时，改写后的地址和 REGISTRY_MAP 仍指向真实仓库。
    # kaniko 会把含 "." 或 ":" 的第一段当成仓库主机，请求绕过代理，构建 token 被直接发给真实仓库
    if address == registry_host.lower():
        raise BuildTokenUnavailable("build registry proxy address must differ from the platform image registry host")

    # 构建容器只持有构建 token。签不出 token 时必须让构建失败，不能改回注入平台账号
    load_active_signing_key()

    return BuildRegistryProxy(
        address=address,
        skip_tls_verify=cluster_annotations.get(ClusterAnnotationKey.BUILD_REGISTRY_PROXY_SKIP_TLS_VERIFY) == "true",
        registry_host=registry_host,
        upstream_alias=alias,
    )


# ------------------
# 失败归类
# ------------------


def make_credential_unavailable_message(reason: str) -> str:
    """构建尚未启动、镜像凭证不可用时展示给用户的提示

    构建过程中代理返回的错误保留在构建日志里，不再另行归类。
    """
    return f"image credential unavailable: {reason}"
