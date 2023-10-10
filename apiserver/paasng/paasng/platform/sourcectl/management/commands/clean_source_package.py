# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
"""清理源码包的脚本
"""
import logging

from django.core.management.base import BaseCommand

from paasng.platform.sourcectl.package.cleaner import delete_from_blob_store
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models.module import Module
from paasng.platform.modules.specs import ModuleSpecs

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理源码包'

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-origin",
            default=SourceOrigin.S_MART,
            required=False,
            type=int,
            help=("Source package type, S-Mart or Lesscode"),
            choices=[origin.value for origin in SourceOrigin],
        )
        parser.add_argument(
            "-max",
            "--max-reserved-num-per-env",
            dest="max_num",
            type=int,
            default=5,
            help="How many package will be reserved in each module, default is 5.",
        )
        parser.add_argument('--dry-run', dest="dry_run", help="dry run", action="store_true")

    def handle(self, source_origin, max_num, dry_run, *args, **options):
        source_origin = SourceOrigin(source_origin)

        for module in Module.objects.filter(source_origin=source_origin.value).order_by("application_id"):
            deleted = self._handle_module(module, max_num=max_num, dry_run=dry_run)
            logger.info("APP %s module %s delete %s source packages", module.application.name, module.name, deleted)

    def _handle_module(self, module: Module, max_num: int = 5, dry_run: bool = True):
        """清理模块的源码包"""
        if not ModuleSpecs(module).deploy_via_package:
            return 0

        deleted = 0
        qs = list(module.packages.filter(is_deleted=False).order_by("created"))[:-max_num]
        for package in qs:
            logger.info("About to clean up the source package %s", package.storage_path)
            package_deleted = False
            deleted += 1
            if not dry_run:
                package_deleted = delete_from_blob_store(package)

            if package_deleted:
                logger.info(
                    "Cleaned up source package %s, reclaimed %s bytes successfully.",
                    package.storage_path,
                    package.package_size,
                )
            else:
                logger.info(
                    "[dry-run] %s bytes will be reclaimed after cleaning the source package %s.",
                    package.package_size,
                    package.storage_path,
                )

        return deleted
