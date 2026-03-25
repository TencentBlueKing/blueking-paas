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

import json
import logging

from blue_krill.storages.blobstore.base import SignatureType
from django.conf import settings
from six import ensure_text

from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import CreateServiceAccountTimeout, ReadTargetStatusTimeout
from paas_wl.infras.resources.base.kres import KNamespace, KPod
from paas_wl.utils.constants import PodPhase
from paas_wl.utils.text import b64encode
from paasng.platform.agent_sandbox.image_build.constants import ImageBuildStatus
from paasng.platform.agent_sandbox.models import ImageBuild
from paasng.utils.blobstore import make_blob_store
from paasng.utils.moby_distribution.registry.utils import parse_image

logger = logging.getLogger(__name__)

# Namespace for image build pods
IMAGE_BUILD_NAMESPACE = "bkpaas-img-build"

# Default build timeout: 5 minutes
_DEFAULT_BUILD_TIMEOUT = 5 * 60


class KanikoBuildExecutor:
    """Manages the full lifecycle of a Kaniko Pod for building container images.

    The executor handles: cluster allocation, Pod creation, log streaming,
    status checking, and Pod cleanup.
    """

    def __init__(self, build: ImageBuild):
        """
        :param build: An ImageBuild model instance.
        """
        self.build = build

        client = self._make_client()
        self.kns = KNamespace(client)
        self.kpod = KPod(client)

        self.pod_name = f"builder-{self.build.uuid.hex}"
        self.namespace = IMAGE_BUILD_NAMESPACE

    def execute(self):
        """Run the full build lifecycle.

        All exceptions are handled internally; ``build.finish_build`` is
        guaranteed to be called before this method returns.
        """
        try:
            self._ensure_namespace()
            self._create_build_pod()
            self._wait_pod_completion()
        except Exception:
            logger.exception("Unexpected error during image build %s", self.build.uuid)
            self.build.finish_build(
                ImageBuildStatus.FAILED,
                build_logs="Unexpected error during image build",
            )
        finally:
            self._cleanup_pod()

    def _make_client(self):
        """Allocate the sandbox cluster and return a Kubernetes API client."""
        cluster = ClusterAllocator(
            AllocationContext(
                tenant_id=self.build.tenant_id,
                region=settings.DEFAULT_REGION_NAME,
                usage="agent_sandbox",
                # agent_sandbox 不区分环境
                environment="",
            )
        ).get_default()
        return get_client_by_cluster_name(cluster.name)

    def _ensure_namespace(self):
        """Ensure the build namespace exists."""
        self.kns.get_or_create(name=self.namespace)
        try:
            self.kns.wait_for_default_sa(self.namespace, timeout=15)
        except CreateServiceAccountTimeout:
            logger.exception("timeout while waiting for the default sa of %s to be created", self.namespace)
            raise

    def _build_env_vars(self) -> list[dict]:
        """Build the environment variables for the Kaniko Pod."""
        output_image_info = parse_image(self.build.output_image)

        env_vars = {
            "SOURCE_GET_URL": self._generate_source_get_url(),
            "OUTPUT_IMAGE": self.build.output_image,
            "DOCKERFILE_PATH": self.build.dockerfile_path,
            "CACHE_REPO": f"{output_image_info.domain}/{output_image_info.name}/dockerbuild-cache",
            "REGISTRY_MIRRORS": settings.KANIKO_REGISTRY_MIRRORS,
            "DOCKER_CONFIG_JSON": self._get_docker_config_json(),
            "SKIP_TLS_VERIFY_REGISTRIES": settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST
            if settings.AGENT_SANDBOX_DOCKER_REGISTRY_SKIP_TLS_VERIFY
            else "",
        }

        if self.build.docker_build_args:
            # 避免 value 有 "," 导致字符分割是异常, 将内容进行 base64 编码
            env_vars["BUILD_ARG"] = ",".join([b64encode(f"{k}={v}") for k, v in self.build.docker_build_args.items()])

        return [{"name": k, "value": str(v)} for k, v in env_vars.items()]

    def _generate_source_get_url(self) -> str:
        """Generate a presigned download URL for the prepared source tarball."""
        if self.build.prepared_source_path:
            bucket = settings.AGENT_SANDBOX_PACKAGE_BUCKET
            store = make_blob_store(bucket)
            return store.generate_presigned_url(
                key=self.build.prepared_source_path,
                expires_in=60 * 60 * 24,
                signature_type=SignatureType.DOWNLOAD,
            )
        return self.build.source_url

    def _get_docker_config_json(self) -> str:
        return b64encode(
            json.dumps(
                {
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
            )
        )

    def _create_build_pod(self):
        """Create the Kaniko build Pod in the sandbox cluster."""
        pod_body = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": self.pod_name,
                "namespace": self.namespace,
                "labels": {
                    "category": "image-builder",
                    "build-id": self.build.uuid.hex,
                    "image-name": self.build.image_name,
                    "image-tag": self.build.image_tag,
                },
            },
            "spec": {
                "containers": [
                    {
                        "name": "builder",
                        "image": settings.KANIKO_IMAGE,
                        "env": self._build_env_vars(),
                        "imagePullPolicy": "IfNotPresent",
                    },
                ],
                "restartPolicy": "Never",
            },
        }
        self.kpod.create_or_update(name=self.pod_name, namespace=self.namespace, body=pod_body)

    def _wait_pod_completion(self):
        """Wait for the build pod to finish, then read logs and persist the result."""
        completion_statuses = {PodPhase.SUCCEEDED, PodPhase.FAILED}
        final_phase = PodPhase.RUNNING
        err_hint = ""
        try:
            final_phase = self.kpod.wait_for_status(
                name=self.pod_name,
                namespace=self.namespace,
                target_statuses=completion_statuses,
                timeout=_DEFAULT_BUILD_TIMEOUT,
            )
        except ReadTargetStatusTimeout:
            err_hint = f"\n\nBuild timed out after {_DEFAULT_BUILD_TIMEOUT} seconds"
        except Exception:
            logger.exception("Unexpected error while waiting for build pod %s", self.build.uuid)
            err_hint = "\n\nUnexpected error while waiting for build pod"

        status = ImageBuildStatus.SUCCESSFUL if final_phase == PodPhase.SUCCEEDED else ImageBuildStatus.FAILED
        self.build.finish_build(status, build_logs=self._read_pod_logs() + err_hint)

    def _read_pod_logs(self) -> str:
        """Read all logs from the build pod."""
        try:
            resp = self.kpod.get_log(name=self.pod_name, namespace=self.namespace)
            return ensure_text(resp.data)
        except Exception:
            logger.exception("Failed to read logs for build %s", self.build.uuid)
            return "Failed to read build logs"

    def _cleanup_pod(self):
        """Delete the Kaniko Pod."""
        try:
            self.kpod.delete(self.pod_name, namespace=self.namespace)
        except Exception:
            logger.exception("Failed to cleanup build pod %s/%s", self.namespace, self.pod_name)
