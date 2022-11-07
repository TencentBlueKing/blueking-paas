# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
from os import PathLike

import requests

from paasng.dev_resources.sourcectl.models import SourcePackage
from paasng.dev_resources.sourcectl.package.utils import parse_url
from paasng.utils.blobstore import StoreType, download_file_from_blob_store

logger = logging.getLogger(__name__)


def download_file_via_http(target_url: str, local_path: PathLike):
    """从目标地址下载文件到目标位置"""

    resp = requests.get(target_url, stream=True)
    if not (resp.status_code >= 200 and resp.status_code < 300):
        raise ValueError(f'The status code returned by the download link({target_url}) is {resp.status_code}')

    with open(local_path, mode="wb") as fh:
        for chunk in resp.iter_content(chunk_size=512):
            if chunk:
                fh.write(chunk)
    return local_path


def download_file_via_url(url: str, local_path: PathLike):
    # download resource form url, s3 is fallback scheme
    logger.debug("[sourcectl] downloading file via url<%s> to local_path<%s>", url, local_path)
    o = parse_url(url)
    if o.store_type in [StoreType.HTTP, StoreType.HTTPS]:
        download_file_via_http(o.url, local_path=local_path)
    else:
        download_file_from_blob_store(bucket=o.bucket, key=o.key, local_path=local_path, store_type=o.store_type)


def download_package(package: SourcePackage, dest_path: PathLike):
    return download_file_via_url(package.storage_url, local_path=dest_path)
