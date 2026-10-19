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

"""沙箱镜像构建接入构建镜像代理：沙箱集群开关开启后，kaniko 构建容器只持有构建 token，经镜像代理访问沙箱镜像仓库"""

import re
import uuid
from typing import TYPE_CHECKING, Mapping

from django.conf import settings

from paasng.platform.engine.configurations.build_token import (
    ANY_TAG,
    BuildTokenAudit,
    BuildTokenScope,
    BuildTokenUnavailable,
    extract_image_tag,
    get_registry_upstream_alias,
    issue_token,
)
from paasng.platform.engine.configurations.image import kaniko_cache_repository
from paasng.platform.engine.configurations.registry_proxy import (
    BuildRegistryProxy,
    is_build_registry_proxy_enabled,
    make_build_registry_proxy,
)

if TYPE_CHECKING:
    from paasng.platform.agent_sandbox.models import ImageBuildRecord

# 仓库路径中单个组成部分的语法，见 https://github.com/distribution/reference
_REPO_COMPONENT_REGEX = re.compile(r"[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*")


def get_image_build_registry_proxy(cluster_annotations: Mapping[str, str]) -> BuildRegistryProxy | None:
    """获取沙箱镜像构建使用的镜像代理，构建不经代理时返回 None

    集群开关开启时检查开启前置条件，任一不满足都必须让构建直接失败，不得回退为注入沙箱仓库的真实凭证。

    :param cluster_annotations: 构建所在沙箱集群的注解
    :raises BuildTokenUnavailable: 集群开关已开启，但开启前置条件不满足
    """
    if not is_build_registry_proxy_enabled(cluster_annotations):
        return None

    host = settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST
    if not host or not settings.AGENT_SANDBOX_DOCKER_REGISTRY_NAMESPACE:
        raise BuildTokenUnavailable("sandbox image registry host or namespace is empty")
    return make_build_registry_proxy(cluster_annotations, host)


def image_build_repository(build: "ImageBuildRecord") -> tuple[str, str]:
    """沙箱镜像构建产物所在的仓库，与 ImageBuildRecord.output_image 的生成规则一致

    :return: (仓库路径, 含主机的完整仓库地址)
    """
    repo_path = f"{settings.AGENT_SANDBOX_DOCKER_REGISTRY_NAMESPACE}/{build.app_code}/{build.image_name}"
    return repo_path, f"{settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST}/{repo_path}"


def make_image_build_scope(build: "ImageBuildRecord") -> BuildTokenScope:
    """沙箱镜像构建的授权范围：仅覆盖本次构建的产物与缓存

    :raises BuildTokenUnavailable: 沙箱仓库配置或产物镜像不满足签发条件
    """
    namespace = settings.AGENT_SANDBOX_DOCKER_REGISTRY_NAMESPACE
    alias = get_registry_upstream_alias(settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST, namespace)

    # 调用方传入的镜像名不得借路径语法越出本应用的仓库目录
    name = f"{build.app_code}/{build.image_name}"
    if not all(_REPO_COMPONENT_REGEX.fullmatch(seg) for seg in name.split("/")):
        raise BuildTokenUnavailable(f"invalid image repository name: {name}")

    repo_path, repository = image_build_repository(build)
    tag = extract_image_tag(build.output_image, repository, "the sandbox image registry repository")

    client_repo = f"{alias}/{repo_path}"
    return BuildTokenScope(
        push=[
            # 允许推送本次构建的产物（具体 tag）
            {"repo": client_repo, "tags": [tag]},
            # 允许推送 kaniko build-cache
            {"repo": kaniko_cache_repository(client_repo), "tags": [ANY_TAG]},
        ],
        # 沙箱仓库中的镜像（含其他应用的沙箱镜像）均可读，推送仅限本次构建
        pull=[f"{alias}/"],
    )


def issue_image_build_token(build: "ImageBuildRecord", cluster_name: str, ttl: int) -> str:
    """为沙箱镜像构建签发构建 token。返回值等同于凭证，不得写入日志

    :param cluster_name: 构建所在沙箱集群名
    :param ttl: 构建的超时时间（秒）
    :raises BuildTokenUnavailable: 未配置签名密钥，或本次构建不满足签发条件
    """
    return issue_token(
        # 统一为带连字符的 36 位格式
        subject=str(uuid.UUID(str(build.uuid))),
        cluster_name=cluster_name,
        ttl=ttl,
        scope=make_image_build_scope(build),
        audit=BuildTokenAudit(app_code=build.app_code),
    )
