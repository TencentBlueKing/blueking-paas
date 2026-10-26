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

import pytest

from paas_wl.bk_app.applications.entities import BuildMetadata
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paasng.platform.engine.configurations.build_token import SigningKey

PROXY = "bkpaas-registry-proxy.example.com"
REGISTRY_HOST = "mirrors.example.com"
REGISTRY_ALIAS = "mirrors-example-com"
REGISTRY_NAMESPACE = "bkpaas/docker"
PLATFORM_PASSWORD = "platform-secret-password"


@pytest.fixture()
def signing_key(settings) -> SigningKey:
    """配置构建 token 的签名密钥"""
    key = SigningKey.generate()
    settings.BUILD_TOKEN_SIGNING_KEYS = [key.to_pem().decode()]
    settings.BUILD_TOKEN_ACTIVE_KID = ""
    return key


@pytest.fixture()
def _platform_registry(settings):
    """平台仓库使用默认配置，且需要跳过证书校验"""
    settings.APP_DOCKER_REGISTRY_HOST = REGISTRY_HOST
    settings.APP_DOCKER_REGISTRY_SKIP_TLS_VERIFY = True
    settings.APP_DOCKER_REGISTRY_NAMESPACE = REGISTRY_NAMESPACE
    settings.APP_DOCKER_REGISTRY_USERNAME = "platform-user"
    settings.APP_DOCKER_REGISTRY_PASSWORD = PLATFORM_PASSWORD


@pytest.fixture()
def dockerfile_metadata(wl_app) -> BuildMetadata:
    """与 DockerBuilder 生成的构建元数据一致"""
    repo = f"{REGISTRY_HOST}/{REGISTRY_NAMESPACE}/{wl_app.paas_app_code}/{wl_app.module_name}"
    return BuildMetadata(
        image=f"{repo}:main-3f2a1bc",
        image_repository=repo,
        use_dockerfile=True,
        extra_envs={
            "DOCKERFILE_PATH": "Dockerfile",
            "BUILD_ARG": "",
            "REGISTRY_MIRRORS": "mirror.example.com",
            "SKIP_TLS_VERIFY_REGISTRIES": REGISTRY_HOST,
        },
    )


def set_cluster_annotations(wl_app: WlApp, **annotations):
    cluster = get_cluster_by_app(wl_app)
    cluster.annotations.update(annotations)
    cluster.save(update_fields=["annotations"])


def enable_registry_proxy(wl_app: WlApp, **annotations):
    set_cluster_annotations(
        wl_app, enable_build_registry_proxy="true", build_registry_proxy_address=PROXY, **annotations
    )
