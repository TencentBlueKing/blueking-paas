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
# and limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import logging

from django.conf import settings

from paasng.utils.moby_distribution.registry.client import DockerRegistryV2Client
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef
from paasng.utils.moby_distribution.registry.utils import parse_image
from paasng.utils.moby_distribution.spec.endpoint import APIEndpoint

from .exceptions import SandboxImageValidateError

logger = logging.getLogger(__name__)


def check_snapshot_image_exists(snapshot: str) -> None:
    """Check if the snapshot image exists in the registry.

    Uses Docker Registry HTTP API V2 to verify the image manifest exists.
    Raises SandboxImageValidateError if image validation fails.

    :param snapshot: The snapshot image name (e.g., "my-registry/my-image:v1").
    """
    named_image = parse_image(snapshot, default_registry=settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST)

    # Reject images from external registries — we only allow images from our configured registry
    if named_image.domain != settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST:
        raise SandboxImageValidateError(
            f"Snapshot image '{snapshot}' is from external registry '{named_image.domain}', "
            f"only images from '{settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST}' are allowed"
        )

    reference = named_image.tag or "latest"
    repo = named_image.name

    try:
        client = DockerRegistryV2Client.from_api_endpoint(
            APIEndpoint(url=settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST),
            username=settings.AGENT_SANDBOX_DOCKER_REGISTRY_USERNAME,
            password=settings.AGENT_SANDBOX_DOCKER_REGISTRY_PASSWORD,
            default_timeout=10,
            https_detect_timeout=5,
            auth_timeout=10,
        )
        if settings.AGENT_SANDBOX_DOCKER_REGISTRY_SKIP_TLS_VERIFY:
            client.session.verify = False
        manifest = ManifestRef(repo=repo, reference=reference, client=client, timeout=10)
        result = manifest.get_metadata()
    except Exception as e:
        raise SandboxImageValidateError(
            f"Failed to check existence of snapshot image '{snapshot}' in registry "
            f"'{settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST}': {e}"
        ) from e

    if result is None:
        raise SandboxImageValidateError(
            f"Snapshot image '{snapshot}' does not exist in registry "
            f"'{settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST}'"
        )
