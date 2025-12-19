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
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.models.build import Build
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


class Command(BaseCommand):
    help = "清理多余的镜像, 保留每个模块最新的 N 个镜像"

    def add_arguments(self, parser):
        parser.add_argument(
            "-max",
            "--max-reserved-num",
            dest="max_reserved_num",
            type=int,
            default=settings.MAX_RESERVED_IMAGES_PER_MODULE,
            help="每个模块最多保留多少个镜像, 默认10个, 最小值0",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="仅显示会删除什么, 不实际删除",
        )

    def handle(self, max_reserved_num, dry_run, *args, **options):
        if max_reserved_num < 0:
            raise CommandError("max_reserved_num 不能小于0")

        # 查询镜像类型的构建记录
        queryset = Build.objects.filter(
            artifact_type=ArtifactType.IMAGE,
            artifact_deleted=False,
            image__isnull=False,
        ).order_by("-created")

        builds_dict: dict[str, list[Build]] = defaultdict(list)
        deleted_count = failed_count = 0

        for build in queryset:
            builds_dict[build.module_id].append(build)

        for builds in builds_dict.values():
            # 对于每个模块，保留最新构建的 max_reserved_num 个镜像
            # Build 按照 created 倒序排列
            need_delete = builds[max_reserved_num:]
            success_delete_builds = []

            for build in need_delete:
                try:
                    success = delete_image_by_build(build, raise_error=True, dry_run=dry_run)
                except ResourceNotFound:
                    # 镜像找不到， 也视为删除成功
                    success = True
                except PermissionDeny as e:
                    success = False
                    self.stdout.write(self.style.ERROR(f"权限不足，无法删除镜像: {build.image}, error: {str(e)}"))
                except Exception as e:
                    success = False
                    self.stdout.write(self.style.ERROR(f"删除镜像失败: {build.image}, error: {str(e)}"))

                if success:
                    build.artifact_deleted = True
                    # bulk_update 不会触发 auto_now 的自动更新, 故手动更新
                    build.updated = timezone.now()
                    success_delete_builds.append(build)

            if not dry_run:
                Build.objects.bulk_update(success_delete_builds, ["artifact_deleted", "updated"])

            deleted_count += len(success_delete_builds)
            failed_count += len(need_delete) - len(success_delete_builds)

        self.stdout.write(
            self.style.SUCCESS(
                ("[DRY-RUN] " if dry_run else "")
                + f"镜像清理完成, 共删除 {deleted_count} 个镜像, 失败 {failed_count} 个镜像"
            )
        )


def delete_image_by_build(
    build: Build,
    raise_error: bool = True,
    dry_run: bool = False,
) -> bool:
    image_info = parse_image(build.image)

    if dry_run:
        logger.info(f"[DRY-RUN] 将删除: {build.image} (ID: {build.uuid})")
        return True

    if not image_info.tag:
        logger.error(f"镜像 {build.image} 不包含 tag 信息，无法删除")
        return False

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
