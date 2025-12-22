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
from typing import NamedTuple, Optional

from django.utils import timezone

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.models import Build
from paas_wl.infras.cluster.utils import get_image_registry_by_app
from paasng.utils.moby_distribution.registry.client import (
    APIEndpoint,
    DockerRegistryV2Client,
)
from paasng.utils.moby_distribution.registry.exceptions import (
    PermissionDeny,
    ResourceNotFound,
)
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


def delete_image(
    build: Build,
    raise_error: bool = True,
    docker_client: Optional[DockerRegistryV2Client] = None,
) -> bool:
    """delete image associated with the given build. if raise_error is True, exceptions will be raised when deletion fails, otherwise False will be returned

    :param build: Build instance
    :param raise_error: whether to raise an exception if deletion fails
    :param docker_client: optional DockerRegistryV2Client instance, if not provided it will be created automatically
    :raise PermissionDeny: when registry deny the deletion
    :raise ResourceNotFound: when image not found in registry
    :raise ValueError: when image tag is missing
    """
    image_info = parse_image(build.image)

    if not image_info.tag:
        logger.error(f"镜像 {build.image} 不包含 tag 信息，无法删除")
        if raise_error:
            raise ValueError("Image tag is required for deletion")
        else:
            return False

    if docker_client is None:
        image_registry = get_image_registry_by_app(build.app)
        docker_client = DockerRegistryV2Client.from_api_endpoint(
            api_endpoint=APIEndpoint(url=image_registry.host),
            username=image_registry.username,
            password=image_registry.password,
        )

    manifest_ref = ManifestRef(
        repo=image_info.name,
        reference=image_info.tag,
        client=docker_client,
    )
    return manifest_ref.delete(raise_not_found=raise_error)


class DeletionResult(NamedTuple):
    deleted: int
    failed: int


def delete_redundant_images(
    module_id: int,
    max_reserved_num: int,
) -> DeletionResult:
    """delete redundant images for a given module, the result was returned as DeletionResult namedtuple

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
        logger.info("模块 %s 镜像数量未超过限制, 无需清理", module_id)
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
            delete_image(b, raise_error=True, docker_client=docker_client)
            success = True
        except PermissionDeny:
            logger.warning("权限不足, 无法删除镜像 %s", b.image)
        except ResourceNotFound:
            # 镜像已不存在，也标记为已删除
            success = True
        except Exception:
            logger.exception("删除镜像 %s 失败", b.image)

        if success:
            deleted_count += 1
            b.artifact_deleted = True
            b.updated = timezone.now()
            success_delete_builds.append(b)
        else:
            failed_count += 1

    Build.objects.bulk_update(success_delete_builds, ["artifact_deleted", "updated"])

    logger.info(
        "模块 %s 镜像清理完成: 总共 %d 个, 成功 %d 个, 失败 %d 个",
        module_id,
        deleted_count + failed_count,
        deleted_count,
        failed_count,
    )
    return DeletionResult(deleted=deleted_count, failed=failed_count)
