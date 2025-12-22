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

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.managers.app_build import delete_redundant_images
from paas_wl.bk_app.applications.models.build import Build

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
            help="The maximum number of images to be reserved for each module. Default is same to settings.MAX_RESERVED_IMAGES_PER_MODULE = %d"
            % settings.MAX_RESERVED_IMAGES_PER_MODULE,
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Just show how many images would be deleted; don't actually delete them.",
        )

    def handle(self, max_reserved_num, dry_run, *args, **options):
        if max_reserved_num < 0:
            raise CommandError("max_reserved_num must be non-negative")

        module_ids = (
            Build.objects.filter(
                artifact_type=ArtifactType.IMAGE,
                artifact_deleted=False,
                image__isnull=False,
                module_id__isnull=False,
            )
            .values_list("module_id", flat=True)
            .distinct()
        )

        deleted_count = failed_count = 0

        for module_id in module_ids:
            if dry_run:
                need_delete = Build.objects.filter(
                    module_id=module_id,
                    artifact_type=ArtifactType.IMAGE,
                    artifact_deleted=False,
                    image__isnull=False,
                ).order_by("-created")[max_reserved_num:]
                deleted_count += len(need_delete)

            else:
                res = delete_redundant_images(
                    module_id=module_id,
                    max_reserved_num=max_reserved_num,
                )
                deleted_count += res.deleted
                failed_count += res.failed

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY-RUN] 预计删除 {deleted_count} 个镜像"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"镜像清理完成, 共删除 {deleted_count} 个镜像, 失败 {failed_count} 个镜像")
            )
