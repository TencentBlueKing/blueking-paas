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
from os import PathLike
from typing import TYPE_CHECKING

from blue_krill.storages.blobstore.exceptions import ObjectAlreadyExists
from django.conf import settings

from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.patcher import patch_smart_tarball
from paasng.platform.sourcectl.exceptions import PackageAlreadyExists
from paasng.platform.sourcectl.models import SourcePackage, SPStat, SPStoragePolicy
from paasng.platform.sourcectl.package.downloader import download_file_via_url
from paasng.platform.sourcectl.utils import generate_temp_dir, generate_temp_file
from paasng.utils.blobstore import make_blob_store

if TYPE_CHECKING:
    from bkpaas_auth.models import User

    from paasng.platform.modules.models import Module


logger = logging.getLogger(__name__)


def upload_to_blob_store(package: PathLike, key: str, allow_overwrite: bool = False) -> str:
    """Upload package to Source Package Bucket

    :param PathLike package: Source package local path
    :param str key: obj key
    :param bool allow_overwrite: Whether to overwrite the original file

    :return str: the full url which describe store type, bucket, key
    """
    logger.debug("[BlobStore] uploading %s to BlobStore[%s]", package, key)
    store = make_blob_store(bucket=settings.BLOBSTORE_BUCKET_AP_PACKAGES)
    try:
        store.upload_file(package, key, allow_overwrite=allow_overwrite)
    except ObjectAlreadyExists as e:
        raise PackageAlreadyExists(str(e))

    return f"{store.STORE_TYPE}://{store.bucket}/{key}"


def generate_storage_path(module: "Module", stat: SPStat) -> str:
    """生成源码包存储在 S3 中的路径"""
    app_info_prefix = f"{module.application.name}/{module.name}"
    package_name = f"{stat.version}:{stat.sha256_signature}:{stat.name}"
    return f"{module.region}/{app_info_prefix}/{package_name}"


def upload_package_via_url(
    module: "Module",
    package_url: str,
    version: str,
    filename: str,
    operator: "User",
    allow_overwrite: bool = True,
    need_patch: bool = False,
) -> "SourcePackage":
    """Upload package to object storage via url path"""
    with generate_temp_file(".tar.gz") as path, generate_temp_dir() as patching_dir:
        download_file_via_url(url=package_url, local_path=path)

        stat = SourcePackageStatReader(path).read()
        # Patch 源码包，如添加 Procfile 文件等
        if need_patch:
            new_path = patch_smart_tarball(tarball_path=path, dest_dir=patching_dir, module=module, stat=stat)
            # 更新 stat
            stat = SourcePackageStatReader(new_path).read()
        else:
            new_path = path

        stat.name = filename
        # 保存版本信息
        if version and stat.version != version:
            logger.warning("The version information parsed from the source package will be overwritten")
            stat.version = version

        obj_key = generate_storage_path(module, stat=stat)
        obj_url = upload_to_blob_store(new_path, key=obj_key, allow_overwrite=allow_overwrite)

    policy = SPStoragePolicy(path=obj_key, url=obj_url, stat=stat, allow_overwrite=allow_overwrite)
    source_package = SourcePackage.objects.store(module, policy, operator=operator)
    return source_package
