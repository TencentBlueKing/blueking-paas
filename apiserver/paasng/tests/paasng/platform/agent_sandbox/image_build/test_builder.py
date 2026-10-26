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

import base64
import json
from types import SimpleNamespace
from typing import Iterator
from unittest import mock

import jwt
import pytest
from django.conf import settings

from paas_wl.infras.resources.base.exceptions import ReadTargetStatusTimeout
from paas_wl.utils.constants import PodPhase
from paasng.platform.agent_sandbox.image_build.builder import _DEFAULT_BUILD_TIMEOUT, KanikoBuildExecutor
from paasng.platform.agent_sandbox.image_build.constants import ImageBuildStatus
from paasng.platform.agent_sandbox.models import ImageBuildRecord
from paasng.platform.engine.configurations.build_token import BuildTokenUnavailable, SigningKey

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

_MODULE = "paasng.platform.agent_sandbox.image_build.builder"
CLUSTER = "sandbox-main"
PROXY = "bkpaas-registry-proxy.example.com"
SOURCE_GET_URL = "https://presigned.url/source"


@pytest.fixture()
def cluster_annotations() -> dict:
    return {}


@pytest.fixture()
def executor(build: ImageBuildRecord, cluster_annotations) -> Iterator[KanikoBuildExecutor]:
    """Create a KanikoBuildExecutor with K8s dependencies mocked out."""
    cluster = SimpleNamespace(name=CLUSTER, annotations=cluster_annotations)
    with (
        mock.patch.object(KanikoBuildExecutor, "_allocate_cluster", return_value=cluster),
        mock.patch(f"{_MODULE}.get_client_by_cluster_name"),
        mock.patch(f"{_MODULE}.KNamespace"),
        mock.patch(f"{_MODULE}.KPod"),
    ):
        executor = KanikoBuildExecutor(build)
    with mock.patch.object(executor, "_generate_source_get_url", return_value=SOURCE_GET_URL):
        yield executor


def _env_dict(executor: KanikoBuildExecutor) -> dict[str, str]:
    return {e["name"]: e["value"] for e in executor._build_env_vars()}


def test_build_env_vars(executor: KanikoBuildExecutor, build: ImageBuildRecord):
    env_dict = _env_dict(executor)

    assert env_dict["OUTPUT_IMAGE"] == build.output_image
    assert env_dict["SOURCE_GET_URL"] == SOURCE_GET_URL
    assert env_dict["DOCKERFILE_PATH"] == "Dockerfile"
    assert (
        env_dict["CACHE_REPO"]
        == f"{settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST}/{settings.AGENT_SANDBOX_DOCKER_REGISTRY_NAMESPACE}/{build.app_code}/{build.image_name}/dockerbuild-cache"
    )
    assert "DOCKER_CONFIG_JSON" in env_dict
    assert "REGISTRY_MAP" not in env_dict
    # "UFlUSE9OX1ZFUlNJT049My4xMQ=="" 是 "PYTHON_VERSION=3.11" b64encode 之后的结果
    assert env_dict["BUILD_ARG"] == "UFlUSE9OX1ZFUlNJT049My4xMQ=="


class TestRegistryProxy:
    HOST = "mirrors.example.com"
    ALIAS = "mirrors-example-com"
    NAMESPACE = "bkpaas-sandbox"
    PASSWORD = "sandbox-secret"

    @pytest.fixture(autouse=True)
    def _setup(self, settings, cluster_annotations, signing_key):
        settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST = self.HOST
        settings.AGENT_SANDBOX_DOCKER_REGISTRY_NAMESPACE = self.NAMESPACE
        settings.AGENT_SANDBOX_DOCKER_REGISTRY_USERNAME = "sandbox-user"
        settings.AGENT_SANDBOX_DOCKER_REGISTRY_PASSWORD = self.PASSWORD
        settings.BUILD_TOKEN_SIGNING_KEYS = [signing_key.to_pem().decode()]
        settings.BUILD_TOKEN_ACTIVE_KID = ""
        cluster_annotations.update(enable_build_registry_proxy="true", build_registry_proxy_address=PROXY)

    @pytest.fixture()
    def signing_key(self) -> SigningKey:
        return SigningKey.generate()

    def _client_repo(self, build: ImageBuildRecord) -> str:
        return f"{self.ALIAS}/{self.NAMESPACE}/{build.app_code}/{build.image_name}"

    def test_env_vars(self, executor, build):
        env_dict = _env_dict(executor)

        client_repo = self._client_repo(build)
        assert env_dict["OUTPUT_IMAGE"] == f"{PROXY}/{client_repo}:{build.image_tag}"
        assert env_dict["CACHE_REPO"] == f"{PROXY}/{client_repo}/dockerbuild-cache"
        assert env_dict["REGISTRY_MAP"] == f"{self.HOST}={PROXY}/{self.ALIAS}"
        assert env_dict["SKIP_DEFAULT_REGISTRY_FALLBACK"] == "true"
        assert env_dict["SKIP_TLS_VERIFY_REGISTRIES"] == ""
        assert env_dict["SOURCE_GET_URL"] == SOURCE_GET_URL
        assert env_dict["BUILD_ARG"] == "UFlUSE9OX1ZFUlNJT049My4xMQ=="

    def test_skip_tls_verify(self, executor, cluster_annotations):
        cluster_annotations["build_registry_proxy_skip_tls_verify"] = "true"

        assert _env_dict(executor)["SKIP_TLS_VERIFY_REGISTRIES"] == PROXY

    def test_only_build_token_in_env(self, executor, build, signing_key):
        """构建容器只持有本次构建的 token，不含沙箱仓库的真实凭证"""
        env_dict = _env_dict(executor)

        assert all(self.PASSWORD not in v for v in env_dict.values())
        auths = json.loads(base64.b64decode(env_dict["DOCKER_CONFIG_JSON"]))["auths"]
        assert list(auths) == [PROXY]
        assert auths[PROXY]["username"] == "bkpaas-build"

        claims = jwt.decode(
            auths[PROXY]["password"],
            signing_key.private_key.public_key(),
            algorithms=["EdDSA"],
            audience=f"bkpaas-registry-proxy:{CLUSTER}",
            issuer="bkpaas-apiserver",
        )
        client_repo = self._client_repo(build)
        assert claims["sub"] == str(build.uuid)
        assert claims["app"] == {"code": build.app_code, "module": ""}
        assert claims["exp"] - claims["iat"] == _DEFAULT_BUILD_TIMEOUT + 300
        assert claims["push"] == [
            {"repo": client_repo, "tags": [build.image_tag]},
            {"repo": f"{client_repo}/dockerbuild-cache", "tags": ["*"]},
        ]
        assert claims["pull"] == [f"{self.ALIAS}/"]
        assert claims["pull_deny"] == []

    @pytest.mark.parametrize(
        ("setup", "reason"),
        [
            (lambda s, a, b: setattr(s, "AGENT_SANDBOX_DOCKER_REGISTRY_NAMESPACE", ""), "host or namespace is empty"),
            (lambda s, a, b: setattr(b, "image_name", "../other"), "invalid image repository name"),
            (lambda s, a, b: setattr(b, "image_name", "My-App"), "invalid image repository name"),
            (lambda s, a, b: setattr(b, "image_tag", "v1@sha256"), "does not belong"),
        ],
    )
    def test_unavailable(self, settings, executor, cluster_annotations, build, setup, reason):
        """开关开启后无法经代理构建时直接失败，不回退为注入真实凭证"""
        setup(settings, cluster_annotations, build)

        with pytest.raises(BuildTokenUnavailable, match=reason):
            executor._build_env_vars()

    def test_execute_fails_without_creating_pod(self, settings, executor, build):
        settings.BUILD_TOKEN_SIGNING_KEYS = []

        executor.execute()

        build.refresh_from_db()
        assert build.status == ImageBuildStatus.FAILED
        assert build.log.content == "image credential unavailable: build token signing key is not configured"
        executor.kpod.create_or_update.assert_not_called()


class TestWaitPodCompletion:
    def test_successful_build(self, executor: KanikoBuildExecutor):
        executor.kpod = mock.MagicMock()
        executor.kpod.wait_for_status.return_value = PodPhase.SUCCEEDED
        executor.kpod.get_log.return_value = mock.MagicMock(data="Build successful!")

        status, build_logs = executor._wait_pod_completion()

        assert status == ImageBuildStatus.SUCCESSFUL
        assert build_logs == "Build successful!"

    def test_failed_build(self, executor: KanikoBuildExecutor):
        executor.kpod = mock.MagicMock()
        executor.kpod.wait_for_status.return_value = PodPhase.FAILED
        executor.kpod.get_log.return_value = mock.MagicMock(data="Error: build failed")

        status, build_logs = executor._wait_pod_completion()

        assert status == ImageBuildStatus.FAILED
        assert build_logs == "Error: build failed"

    def test_timeout(self, executor: KanikoBuildExecutor):
        executor.kpod = mock.MagicMock()
        executor.kpod.wait_for_status.side_effect = ReadTargetStatusTimeout(
            pod_name="test-pod", max_seconds=_DEFAULT_BUILD_TIMEOUT
        )
        executor.kpod.get_log.return_value = mock.MagicMock(data="Start building...")

        status, build_logs = executor._wait_pod_completion()

        assert status == ImageBuildStatus.FAILED
        assert build_logs == f"Start building...\n\nBuild timed out after {_DEFAULT_BUILD_TIMEOUT} seconds"
