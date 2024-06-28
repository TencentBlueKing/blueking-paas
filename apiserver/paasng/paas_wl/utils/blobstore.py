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

"""BlobStore client
"""
import logging
from typing import Optional

from blue_krill.data_types.enum import EnumField, StructuredEnum
from blue_krill.storages.blobstore.base import BlobStore
from blue_krill.storages.blobstore.bkrepo import BKGenericRepo
from blue_krill.storages.blobstore.s3 import S3Store
from django.conf import settings

logger = logging.getLogger(__name__)


class StoreType(str, StructuredEnum):
    S3 = EnumField("s3")
    BKREPO = EnumField("bkrepo")


def detect_default_blob_store() -> StoreType:
    """如果没有指定 StoreType，且已有 BKRepo 配置，则优先使用"""
    store_type = settings.BLOBSTORE_TYPE
    if store_type and store_type in [StoreType.S3, StoreType.BKREPO]:
        return store_type

    if hasattr(settings, "BLOBSTORE_BKREPO_CONFIG") and settings.BLOBSTORE_BKREPO_CONFIG:
        return StoreType.BKREPO
    else:
        return StoreType.S3


def make_blob_store(bucket: str, store_type: Optional[StoreType] = None, **kwargs) -> BlobStore:
    if store_type is None:
        store_type = detect_default_blob_store()

    store_type = StoreType(store_type)
    if store_type == StoreType.BKREPO:
        config = settings.BLOBSTORE_BKREPO_CONFIG
        return BKGenericRepo(
            bucket=bucket,
            project=config["PROJECT"],
            endpoint_url=config["ENDPOINT"],
            username=config["USERNAME"],
            password=config["PASSWORD"],
        )
    return S3Store(
        bucket=bucket,
        aws_access_key_id=settings.BLOBSTORE_S3_ACCESS_KEY,
        aws_secret_access_key=settings.BLOBSTORE_S3_SECRET_KEY,
        endpoint_url=settings.BLOBSTORE_S3_ENDPOINT,
        region_name=settings.BLOBSTORE_S3_REGION_NAME,
        signature_version=settings.BLOBSTORE_S3_SIG_VERSION,
    )
