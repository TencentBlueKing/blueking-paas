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

import json
import logging
from typing import TYPE_CHECKING

from django.conf import settings

from paas_wl.infras.resources.base.kres import KSecret
from paas_wl.utils.text import b64encode

if TYPE_CHECKING:
    from kubernetes.dynamic import DynamicClient

logger = logging.getLogger(__name__)

IMAGE_CREDENTIAL_NAME = "sandbox-image-credential"


def generate_dockerconfig_b64() -> str:
    """生成 base64 编码的 Docker Registry 认证配置。

    基于全局配置的 registry 账号信息，构造符合 kubernetes.io/dockerconfigjson 格式的认证配置，
    并返回 base64 编码后的 JSON 字符串。

    :return: base64 编码的 Docker 认证配置 JSON 字符串
    """
    config = {
        "auths": {
            settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST: {
                "username": settings.AGENT_SANDBOX_DOCKER_REGISTRY_USERNAME,
                "password": settings.AGENT_SANDBOX_DOCKER_REGISTRY_PASSWORD,
                "auth": b64encode(
                    f"{settings.AGENT_SANDBOX_DOCKER_REGISTRY_USERNAME}:{settings.AGENT_SANDBOX_DOCKER_REGISTRY_PASSWORD}"
                ),
            }
        }
    }
    return b64encode(json.dumps(config))


def ensure_image_credential(
    client: "DynamicClient",
    namespace: str,
) -> str:
    """确保镜像拉取凭证在指定集群和命名空间中存在。

    :param client: K8s API 客户端。
    :param namespace: 目标命名空间。
    :return: 凭证名称。
    """
    secret_body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "type": "kubernetes.io/dockerconfigjson",
        "metadata": {
            "name": IMAGE_CREDENTIAL_NAME,
            "namespace": namespace,
        },
        "data": {".dockerconfigjson": generate_dockerconfig_b64()},
    }

    # 使用 get_or_create 避免不必要的更新操作(沙箱提速)。目前，凭证由平台统一管理，内容稳定无需每次同步
    KSecret(client).get_or_create(name=IMAGE_CREDENTIAL_NAME, namespace=namespace, body=secret_body)

    return IMAGE_CREDENTIAL_NAME
