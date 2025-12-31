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
import os
import pathlib
import shutil
import tempfile
from typing import cast

from django.core.management.base import BaseCommand

from paasng.platform.modules.constants import AppImageType
from paasng.platform.smart_app.conf import bksmart_settings
from paasng.utils.moby_distribution import APIEndpoint, DockerRegistryV2Client, ImageRef
from paasng.utils.moby_distribution.registry.utils import parse_image
from paasng.utils.validators import str2bool

logger = logging.getLogger(__name__)


def get_image_config(image_type: str, base_image_id: str) -> dict[str, str]:
    if image_type == AppImageType.LEGACY.value:
        return {
            "repo": bksmart_settings.base_image.name,
            "reference": bksmart_settings.base_image.tag,
        }

    if image_type == AppImageType.CNB.value:
        return {
            "repo": bksmart_settings.cnb_base_image.get_name(base_image_id),
            "reference": bksmart_settings.cnb_base_image.get_tag(base_image_id),
        }

    raise ValueError(f"Unsupported image type: {image_type}")


class Command(BaseCommand):
    help = "管理 S-Mart 基础镜像"

    def add_arguments(self, parser):
        parser.add_argument("--image", required=True, help="universal image")
        parser.add_argument(
            "--type",
            required=True,
            dest="type_",
            help="image type can be either cnb or legacy",
        )
        parser.add_argument("--base-image-id", dest="base_image_id", default="default", help="dest cnb base image id")
        parser.add_argument("--dry-run", dest="dry_run", type=str2bool, help="dry run", default=False)

    def handle(self, image: str, type_: str, base_image_id: str, dry_run: bool, *args, **options):
        if dry_run:
            logger.warning("Skipped the step of pushing S-Mart base image to bkrepo!")
            return

        from_image = parse_image(image)
        image_tarball_path = pathlib.Path(tempfile.mktemp())
        try:
            ref = ImageRef.from_image(
                from_repo=from_image.name,
                from_reference=cast(str, from_image.tag),
                client=DockerRegistryV2Client.from_api_endpoint(APIEndpoint(url=from_image.domain)),
            )
            ref.save(dest=str(image_tarball_path))
        except Exception:
            if image_tarball_path.exists():
                image_tarball_path.unlink()
            raise

        workplace = tempfile.mkdtemp()
        to_config = get_image_config(type_, base_image_id)

        try:
            ref = ImageRef.from_tarball(
                workplace=pathlib.Path(workplace),
                src=image_tarball_path,
                to_repo=to_config["repo"],
                to_reference=to_config["reference"],
                client=bksmart_settings.registry.get_client(),
            )
            ref.push()
        finally:
            os.unlink(image_tarball_path)
            shutil.rmtree(workplace)
