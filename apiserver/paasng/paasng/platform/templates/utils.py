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
import tempfile
from os import PathLike
from pathlib import Path
from typing import Optional

from paasng.platform.sourcectl.utils import uncompress_directory
from paasng.utils.blobstore import StoreType, download_file_from_blob_store

logger = logging.getLogger(__name__)


def download_from_blob_store(
    bucket: str, s3_path: PathLike, local_path=None, store_type: Optional[StoreType] = None
) -> Path:
    """[Deprecated] Download template from BlobStore
    Deprecated: use download_file_from_blob_store directly

    :param bucket: 存放模板的 bucket
    :param s3_path: 模板 tar 包在 BlobStore 上的存储路径
    :param local_path: 如果提供 local_path, 则将 tar 包解压到指定的 local_path, 如果不提供, 则解压缩至随机生成的 local_path
    :param store_type: 首选的 store 类型, 如果为 None, 则使用系统默认的 blobstore
    """
    if not local_path:
        local_path = tempfile.mkdtemp()
    local_path = Path(local_path)
    local_path.mkdir(exist_ok=True)
    # make path to download.
    tar_path = Path(f"{local_path}/{Path(s3_path).name}")
    # download template from blob_store
    download_file_from_blob_store(bucket=bucket, key=str(s3_path), local_path=tar_path, store_type=store_type)
    uncompress_directory(source_path=str(tar_path), target_path=local_path)
    tar_path.unlink()
    return local_path


def uncompress_tar_to_local_path(src: PathLike, local_path=None) -> Path:
    """解压一个本地目录下的 tar 包至 local_path
    :param src: tar 包文件的地址
    :param local_path: 如果提供 local_path, 则将 tar 包解压到指定的 local_path, 如果不提供, 则解压缩至随机生成的 local_path
    """
    if not local_path:
        local_path = tempfile.mkdtemp()
    local_path = Path(local_path)
    local_path.mkdir(exist_ok=True)
    uncompress_directory(source_path=src, target_path=local_path)
    return local_path
