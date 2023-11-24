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
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings

from paasng.utils.blobstore import StoreType, detect_default_blob_store


@dataclass
class BlobObject:
    store_type: StoreType
    bucket: str
    key: str
    url: str


def parse_url(url: str) -> BlobObject:
    """解析 s3/bkrpeo 协议的 url"""
    o = urlparse(url)
    if o.scheme == "":
        # 向前兼容, 如果 url 不带上协议， 则使用默认的类型.
        return BlobObject(
            store_type=detect_default_blob_store(),
            bucket=settings.BLOBSTORE_BUCKET_AP_PACKAGES,
            key=url,
            url=url,
        )

    path = Path(o.path)
    bucket = o.netloc
    if path.is_absolute():
        # Ceph RGW 不支持绝对路径
        path = path.relative_to("/")
    return BlobObject(
        store_type=StoreType(o.scheme),
        bucket=bucket,
        key=str(path),
        url=url,
    )
