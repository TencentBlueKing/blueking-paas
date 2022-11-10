# -*- coding: utf-8 -*-
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
