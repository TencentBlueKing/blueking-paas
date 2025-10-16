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

import contextlib
import logging
import os
import pathlib
import shutil
import tempfile
import urllib3
import requests
from typing import Dict, cast

from django.core.management.base import BaseCommand

from paasng.platform.modules.constants import AppImageType
from paasng.platform.smart_app.conf import bksmart_settings
from paasng.utils.moby_distribution import APIEndpoint, DockerRegistryV2Client, ImageRef
from paasng.utils.moby_distribution.registry.utils import parse_image
from paasng.utils.validators import str2bool

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def patch_ssl_verification(skip_verify: bool):
    """Context manager to temporarily disable SSL verification if needed."""
    if skip_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("SSL certificate verification is disabled. This should only be used with trusted registries.")
        
        # 保存原始的requests方法
        original_request = requests.request
        original_session_request = requests.Session.request
        
        # 创建新的request方法，强制设置verify=False
        def patched_request(*args, **kwargs):
            kwargs['verify'] = False
            return original_request(*args, **kwargs)
        
        def patched_session_request(self, *args, **kwargs):
            kwargs['verify'] = False
            return original_session_request(self, *args, **kwargs)
        
        try:
            # 替换requests的方法
            requests.request = patched_request
            requests.Session.request = patched_session_request
            yield
        finally:
            # 恢复原始的requests方法
            requests.request = original_request
            requests.Session.request = original_session_request
    else:
        yield


DEST_IMAGE_CONFIGS: Dict[str, Dict] = {
    AppImageType.CNB.value: {
        "repo": bksmart_settings.cnb_base_image.name,
        "reference": bksmart_settings.cnb_base_image.tag,
    },
    AppImageType.LEGACY.value: {
        "repo": bksmart_settings.base_image.name,
        "reference": bksmart_settings.base_image.tag,
    },
}


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
        parser.add_argument("--dry-run", dest="dry_run", type=str2bool, help="dry run", default=False)
        parser.add_argument("--skip-verify", dest="skip_verify", type=str2bool, help="skip SSL certificate verification", default=False)

    def handle(self, image: str, type_: str, dry_run: bool, skip_verify: bool, *args, **options):
        if dry_run:
            logger.warning("Skipped the step of pushing S-Mart base image to bkrepo!")
            return

        with patch_ssl_verification(skip_verify):
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
            to_config = DEST_IMAGE_CONFIGS[type_]

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
