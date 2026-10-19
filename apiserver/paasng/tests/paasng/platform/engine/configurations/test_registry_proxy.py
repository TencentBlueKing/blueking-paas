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

from types import SimpleNamespace
from typing import Dict
from unittest import mock

import pytest

from paas_wl.bk_app.applications.entities import BuildMetadata
from paas_wl.infras.cluster.entities import AppImageRegistry
from paasng.platform.engine.configurations.build_token import BuildTokenUnavailable, SigningKey
from paasng.platform.engine.configurations.registry_proxy import (
    BuildRegistryProxy,
    get_build_registry_proxy,
)

PROXY = "bkpaas-registry-proxy.example.com"
HOST = "mirrors.tencent.com"
ALIAS = "mirrors-tencent-com"
NAMESPACE = "bkpaas/docker"
DOCKERFILE_METADATA = BuildMetadata(image=f"{HOST}/{NAMESPACE}/demo/default:v1", use_dockerfile=True)


def _annotations(**overrides) -> Dict:
    annos = {"enable_build_registry_proxy": "true", "build_registry_proxy_address": PROXY}
    annos.update(overrides)
    return {k: v for k, v in annos.items() if v is not None}


@pytest.fixture()
def _with_signing_key(settings):
    settings.BUILD_TOKEN_SIGNING_KEYS = [SigningKey.generate().to_pem().decode()]
    settings.BUILD_TOKEN_ACTIVE_KID = ""


@pytest.fixture()
def cluster_annotations() -> Dict:
    return _annotations()


@pytest.fixture()
def registry() -> AppImageRegistry:
    return AppImageRegistry(
        host=HOST, skip_tls_verify=False, namespace=NAMESPACE, username="bkpaas", password="platform-secret"
    )


@pytest.fixture()
def _mock_cluster(cluster_annotations, registry):
    """mock 应用所在集群的注解与平台仓库"""
    with (
        mock.patch(
            "paasng.platform.engine.configurations.registry_proxy.get_cluster_by_app",
            return_value=SimpleNamespace(annotations=cluster_annotations),
        ),
        mock.patch(
            "paasng.platform.engine.configurations.registry_proxy.get_image_registry_by_app", return_value=registry
        ),
    ):
        yield


@pytest.mark.usefixtures("_with_signing_key", "_mock_cluster")
class TestGetBuildRegistryProxy:
    @pytest.mark.parametrize(
        ("address", "reason"),
        [
            (None, "not configured"),
            (HOST, "must differ from the platform image registry host"),
        ],
    )
    def test_invalid_address(self, cluster_annotations, address, reason):
        cluster_annotations.pop("build_registry_proxy_address")
        if address is not None:
            cluster_annotations["build_registry_proxy_address"] = address

        with pytest.raises(BuildTokenUnavailable, match=reason):
            get_build_registry_proxy(mock.MagicMock(), DOCKERFILE_METADATA)

    @pytest.mark.parametrize(
        ("host", "namespace", "reason"),
        [
            ("", NAMESPACE, "host or namespace is empty"),
            (HOST, "", "host or namespace is empty"),
            ("[::1]:5000", NAMESPACE, "cannot derive an upstream alias"),
        ],
    )
    def test_invalid_registry(self, registry, host, namespace, reason):
        registry.host = host
        registry.namespace = namespace

        with pytest.raises(BuildTokenUnavailable, match=reason):
            get_build_registry_proxy(mock.MagicMock(), DOCKERFILE_METADATA)

    def test_signing_key_not_configured(self, settings):
        settings.BUILD_TOKEN_SIGNING_KEYS = []

        with pytest.raises(BuildTokenUnavailable, match="signing key is not configured"):
            get_build_registry_proxy(mock.MagicMock(), DOCKERFILE_METADATA)


class TestBuildRegistryProxy:
    @pytest.fixture()
    def proxy(self) -> BuildRegistryProxy:
        return BuildRegistryProxy(address=PROXY, skip_tls_verify=False, registry_host=HOST, upstream_alias=ALIAS)

    @pytest.mark.parametrize("reference", [f"{HOST}.evil.com/{NAMESPACE}/demo/default", "demo/default:v1", HOST])
    def test_rewrite_other_registry(self, proxy, reference):
        with pytest.raises(BuildTokenUnavailable, match="does not belong to the platform image registry"):
            proxy.rewrite(reference)
