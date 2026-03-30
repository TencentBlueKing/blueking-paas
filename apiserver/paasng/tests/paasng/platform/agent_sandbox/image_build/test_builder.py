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

from unittest import mock

import pytest
from django.conf import settings

from paas_wl.infras.resources.base.exceptions import ReadTargetStatusTimeout
from paas_wl.utils.constants import PodPhase
from paasng.platform.agent_sandbox.image_build.builder import _DEFAULT_BUILD_TIMEOUT, KanikoBuildExecutor
from paasng.platform.agent_sandbox.image_build.constants import ImageBuildStatus
from paasng.platform.agent_sandbox.models import ImageBuildRecord

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def executor(build: ImageBuildRecord) -> KanikoBuildExecutor:
    """Create a KanikoBuildExecutor with K8s dependencies mocked out."""
    _module = "paasng.platform.agent_sandbox.image_build.builder"
    with (
        mock.patch.object(KanikoBuildExecutor, "_make_client", return_value=mock.MagicMock()),
        mock.patch(f"{_module}.KNamespace"),
        mock.patch(f"{_module}.KPod"),
    ):
        return KanikoBuildExecutor(build)


def test_build_env_vars(executor: KanikoBuildExecutor, build: ImageBuildRecord):
    source_get_url = "https://presigned.url/source"

    with mock.patch.object(executor, "_generate_source_get_url", return_value=source_get_url):
        env_list = executor._build_env_vars()

    env_dict = {e["name"]: e["value"] for e in env_list}
    assert env_dict["OUTPUT_IMAGE"] == build.output_image
    assert env_dict["SOURCE_GET_URL"] == source_get_url
    assert env_dict["DOCKERFILE_PATH"] == "Dockerfile"
    assert (
        env_dict["CACHE_REPO"]
        == f"{settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST}/{settings.AGENT_SANDBOX_DOCKER_REGISTRY_NAMESPACE}/{build.app_code}/{build.image_name}/dockerbuild-cache"
    )
    # "UFlUSE9OX1ZFUlNJT049My4xMQ=="" 是 "PYTHON_VERSION=3.11" b64encode 之后的结果
    assert env_dict["BUILD_ARG"] == "UFlUSE9OX1ZFUlNJT049My4xMQ=="


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
