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
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from paasng.platform.templates.command import EnhancedTemplateCommand
from paasng.platform.templates.constants import RenderMethod, TemplateType
from paasng.platform.templates.exceptions import TmplNotExists
from paasng.platform.templates.fixtures import ProcfileFixture
from paasng.platform.templates.models import Template
from paasng.platform.templates.utils import StoreType, download_from_blob_store, uncompress_tar_to_local_path

logger = logging.getLogger(__name__)

DEFAULT_EXECUTABLE_FILES = [
    "bin/pre-compile",
    "bin/pre_compile",
    "bin/post-compile",
    "bin/post_compile",
]


class Templater:
    def __init__(
        self,
        tmpl_name: str,
        type: TemplateType,
        region: str,
        owner_username: str,
        app_code: str,
        app_secret: str,
        app_name: str,
    ):
        try:
            tmpl: Template = Template.objects.get(name=tmpl_name, type=type)
        except ObjectDoesNotExist:
            raise TmplNotExists(f"Template <{tmpl_name}>, Type <{type}> does not exists")

        self.tmpl = tmpl
        self.command = EnhancedTemplateCommand(
            render_method=RenderMethod(tmpl.render_method),
            force_executable_files=DEFAULT_EXECUTABLE_FILES,
        )
        self.region = region

        # 渲染模板用的配置上下文
        self.context = {
            "region": region,
            "app_code": app_code,
            "app_secret": app_secret,
            "app_name": app_name,
            "owner_username": owner_username,
            "BK_URL": settings.COMPONENT_SYSTEM_HOST_IN_TEST,
            "BK_LOGIN_URL": settings.LOGIN_FULL,
        }

    def download_tmpl(self) -> Path:
        """Download current app template to a local temp directory"""
        location = self.tmpl.blob_url
        o = urlparse(location)
        scheme, bucket, path = o.scheme.lower(), o.netloc, Path(o.path)
        logger.debug("checkout template from [%s: %s]", scheme, location)
        if scheme == "file":
            return uncompress_tar_to_local_path(path)

        if path.is_absolute():
            # Ceph RGW 不支持绝对路径
            path = path.relative_to("/")

        store_type = {"s3": StoreType.S3, "bkrepo": StoreType.BKREPO}.get(scheme)
        if not store_type:
            logger.warning("unknown protocol type: %s, url: %s", o.scheme, location)

        return download_from_blob_store(bucket, path, store_type=store_type)

    def write_to_dir(self, target_path: Path):
        """Write the rendered templated source codes into one directory"""
        path = self.download_tmpl()
        self.command.handle(str(target_path), template=str(path), context=self.context)

        # Write procfile
        if self.tmpl.processes:
            ProcfileFixture(project_root=str(target_path), context=self.context).setup(processes=self.tmpl.processes)
