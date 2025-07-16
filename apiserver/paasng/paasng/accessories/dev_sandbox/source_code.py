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

from blue_krill.storages.blobstore.base import SignatureType
from django.conf import settings

from paasng.platform.engine.utils.source import validate_source_dir_str
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.models import VersionInfo
from paasng.platform.sourcectl.repo_controller import get_repo_controller
from paasng.platform.sourcectl.utils import compress_directory_ext, generate_temp_dir, generate_temp_file
from paasng.utils.blobstore import make_blob_store

logger = logging.getLogger(__name__)


def upload_source_code(module: Module, version_info: VersionInfo, source_dir: str, operator: str) -> str:
    """
    上传应用模块源码到对象存储, 并且返回源码的下载链接
    参考方法 "BaseBuilder.compress_and_upload"

    :return: 获取源码包的链接（带签名的对象存储链接）
    """
    # 仅支持 OAuth 授权的代码库
    if module.get_source_origin() != SourceOrigin.AUTHORIZED_VCS:
        raise NotImplementedError

    with generate_temp_dir() as working_dir:
        # 下载源码到临时目录
        full_source_dir = validate_source_dir_str(working_dir, source_dir)
        get_repo_controller(module, operator=operator).export(working_dir, version_info)

        # 上传源码包到对象存储
        with generate_temp_file(suffix=".tar.gz") as package_path:
            source_destination_path = _get_source_package_path(
                version_info, module.application.code, module.name, module.region
            )
            compress_directory_ext(full_source_dir, package_path)
            logger.info(f"Uploading source files to {source_destination_path}")
            store = make_blob_store(bucket=settings.BLOBSTORE_BUCKET_APP_SOURCE)
            store.upload_file(package_path, source_destination_path)

    return store.generate_presigned_url(
        key=source_destination_path,
        expires_in=60 * 60 * 24,
        signature_type=SignatureType.DOWNLOAD,
    )


def _get_source_package_path(version_info: VersionInfo, app_code: str, module_name: str, region: str) -> str:
    """Return the blobstore path for storing source files package"""
    branch = version_info.version_name
    revision = version_info.revision

    slug_name = f"{app_code}:{module_name}:{branch}:{revision}:dev"
    return f"{region}/home/{slug_name}/tar"
