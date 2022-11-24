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
"""BlobStore client
"""
import json
import logging
import urllib.parse
from os import PathLike
from textwrap import dedent
from typing import Dict, Optional

import boto3
from bkstorages.backends.bkrepo import BKRepoStorage
from bkstorages.backends.rgw import RGWBoto3Storage
from blue_krill.data_types.enum import EnumField, StructuredEnum
from blue_krill.storages.blobstore.base import BlobStore
from blue_krill.storages.blobstore.bkrepo import BKGenericRepo
from blue_krill.storages.blobstore.s3 import S3Store
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.encoding import force_bytes, force_text

logger = logging.getLogger(__name__)


class StoreType(str, StructuredEnum):
    S3 = EnumField("s3")
    BKREPO = EnumField("bkrepo")
    # 向前兼容, 支持 http/https 协议
    HTTP = EnumField("http")
    HTTPS = EnumField("https")


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


def get_storage_by_bucket(bucket: str, store_type: Optional[str] = None):
    """When current store_type is S3, this function may create the bucket if not exists

    :param store_type: "bkrepo" or "s3"
    """
    if store_type is None:
        store_type = detect_default_blob_store()

    store_type = StoreType(store_type)

    if store_type == StoreType.BKREPO:
        config = settings.BLOBSTORE_BKREPO_CONFIG
        return BKRepoStorage(
            bucket=bucket,
            project_id=config["PROJECT"],
            endpoint_url=config["ENDPOINT"],
            username=config["USERNAME"],
            password=config["PASSWORD"],
        )
    else:
        s3 = boto3.resource(
            's3',
            aws_access_key_id=settings.RGW_ACCESS_KEY_ID,
            aws_secret_access_key=settings.RGW_SECRET_ACCESS_KEY,
            endpoint_url=settings.RGW_ENDPOINT_URL,
        )
        try:
            s3.Bucket(bucket)
            s3.meta.client.head_bucket(Bucket=bucket)
        except ClientError as e:
            # If a client error is thrown, then check that it was a 404 error.
            # If it was a 404 error, then the bucket does not exist.
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                s3.create_bucket(Bucket=bucket)
            else:
                raise

        return RGWBoto3Storage(
            bucket=bucket,
            access_key=settings.RGW_ACCESS_KEY_ID,
            secret_key=settings.RGW_SECRET_ACCESS_KEY,
            endpoint_url=settings.RGW_ENDPOINT_URL,
        )


def generate_s3cmd_conf(endpoint, access_key, secret_key, region_name, sig_version, encrypt: bool = False):
    """Generate conf file for s3cmd so docker container can download & put files on S3
    Server.
    """
    ret = urllib.parse.urlparse(endpoint)
    signature_v2 = not (sig_version == 's3v4')
    return dedent(
        f"""\
        # Setup endpoint
        host_base = {ret.netloc}
        host_bucket = {ret.netloc}
        bucket_location = {region_name}
        use_https = False

        # Setup access keys
        access_key = {encrypt_slug_config(access_key) if encrypt else access_key}
        secret_key = {encrypt_slug_config(secret_key) if encrypt else secret_key}

        # Enable S3 v4 signature APIs
        signature_v2 = {signature_v2}
    """
    )


def make_blob_store_env(encrypt: bool = False) -> Dict[str, str]:
    store = make_blob_store(settings.BLOBSTORE_BUCKET_APP_SOURCE)
    if isinstance(store, S3Store):
        return {
            "S3CMD_CONF": generate_s3cmd_conf(
                endpoint=store.endpoint_url,
                access_key=store.aws_access_key_id,
                secret_key=store.aws_secret_access_key,
                region_name=store.region_name,
                sig_version=store.signature_version,
                encrypt=encrypt,
            )
        }
    elif isinstance(store, BKGenericRepo):
        return {
            "BKREPO_CONF": json.dumps(
                dict(
                    endpoint=f"{store.endpoint_url}/generic/",
                    project=store.project,
                    bucket=store.bucket,
                    user=store.username,
                    password=encrypt_slug_config(store.password) if encrypt else store.password,
                )
            )
        }
    raise NotImplementedError


def encrypt_slug_config(raw_content: str) -> str:
    f = Fernet(settings.SLUG_ENCRYPT_SECRET_KEY)
    return force_text(f.encrypt(force_bytes(raw_content)))


def download_file_from_blob_store(bucket: str, key: str, local_path: PathLike, store_type: Optional[StoreType] = None):
    """Download file to filepath
    :param str bucket: 对象所在的桶/仓库
    :param str key: 需要下载的对象的 key
    :param local_path: 文件下载至的路径
    :param str store_type: 首选的 blob store 类型
    """
    store = make_blob_store(bucket, store_type=store_type)
    store.download_file(key=key, filepath=local_path)
