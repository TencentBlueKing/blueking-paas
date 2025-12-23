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
from typing import NamedTuple

from django.utils import timezone

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.models import Build
from paas_wl.infras.cluster.utils import get_image_registry_by_app
from paasng.utils.moby_distribution.registry.client import APIEndpoint, DockerRegistryV2Client
from paasng.utils.moby_distribution.registry.exceptions import PermissionDeny, ResourceNotFound
from paasng.utils.moby_distribution.registry.resources.manifests import ManifestRef
from paasng.utils.moby_distribution.registry.utils import parse_image

logger = logging.getLogger(__name__)


def mark_as_latest_artifact(build: "Build"):
    """mark the given build as latest artifact"""
    if build.artifact_type != ArtifactType.IMAGE:
        return
    # 旧的同名镜像会被覆盖, 则标记为已删除
    qs = Build.objects.filter(module_id=build.module_id, image=build.image).exclude(uuid=build.uuid)
    qs.update(artifact_deleted=True)
    return


class DeletionResult(NamedTuple):
    deleted: int
    failed: int


def delete_redundant_images(
    module_id: int,
    max_reserved_num: int,
) -> DeletionResult:
    """delete redundant images by module id, the result was returned as DeletionResult namedtuple

    :param module_id: id of the module
    :param max_reserved_num: maximum number of images to be reserved
    """
    builds = Build.objects.filter(
        module_id=module_id,
        artifact_type=ArtifactType.IMAGE,
        artifact_deleted=False,
        image__isnull=False,
    ).order_by("-created")[max_reserved_num:]

    if not builds:
        logger.info(f"module {module_id} image count within limit, no need to clean up")
        return DeletionResult(deleted=0, failed=0)

    deleted_count = 0
    failed_count = 0
    success_delete_builds = []

    image_registry = get_image_registry_by_app(builds[0].app)
    docker_client = DockerRegistryV2Client.from_api_endpoint(
        api_endpoint=APIEndpoint(url=image_registry.host),
        username=image_registry.username,
        password=image_registry.password,
    )

    for b in builds:
        success = False
        try:
            image_info = parse_image(b.image)
            if not image_info.tag:
                raise ValueError(f"image tag missing, build id: {b.id}, image: {b.image}")  # noqa: TRY301

            manifest_ref = ManifestRef(
                repo=image_info.name,
                reference=image_info.tag,
                client=docker_client,
            )
            success = manifest_ref.delete(raise_not_found=True)
        except PermissionDeny:
            logger.warning(f"delete image {b.image} permission denied, registry: {image_registry.host}")
        except ResourceNotFound:
            # 镜像已不存在，也标记为已删除
            success = True
        except Exception:
            logger.exception(f"delete image {b.image} failed, registry: {image_registry.host}")

        if success:
            deleted_count += 1
            b.artifact_deleted = True
            # https://stackoverflow.com/questions/64116500/update-auto-now-field-in-bulk-update
            # https://docs.djangoproject.com/en/6.0/ref/models/querysets/#bulk-update
            # bulk_update not call save method, so auto_now will not work here, manually update
            b.updated = timezone.now()
            success_delete_builds.append(b)
        else:
            failed_count += 1

    Build.objects.bulk_update(success_delete_builds, ["artifact_deleted", "updated"])

    logger.info(f"module {module_id} image cleanup completed, deleted: {deleted_count}, failed: {failed_count}")
    return DeletionResult(deleted=deleted_count, failed=failed_count)
