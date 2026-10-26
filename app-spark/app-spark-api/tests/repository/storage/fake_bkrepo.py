# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""In-memory stand-in for blue_krill's ``BKGenericRepo``.

Replaces the HTTP client underneath :class:`~app_spark_api.repository.storage.blob_stores.BkRepo`
rather than ``BkRepo`` itself, so the configuration check and the argument mapping in our own
wrapper still run.
"""

from __future__ import annotations

import io
import shutil
from typing import Any, BinaryIO

import requests
from blue_krill.storages.blobstore.exceptions import DownloadFailedError, RequestError, UploadFailedError

BKREPO_CONFIG = {
    "PROJECT": "bkpaas",
    "ENDPOINT": "https://bkrepo.example.com",
    "USERNAME": "username",
    "PASSWORD": "password",
}


class FakeBkRepoServer:
    """The objects a fake BkRepo holds, shared by every client built while it is installed.

    :ivar objects: Stored blobs keyed by ``(bucket, key)``.
    :ivar signed: Every ``(bucket, key, expires_in)`` a URL was signed for.
    :ivar fail_uploads: Make the next uploads fail the way blue_krill reports it.
    :ivar fail_signing: Make signing fail the way blue_krill reports it.
    :ivar fail_deletes: Make deletes fail the way an unreachable BkRepo does, which blue_krill
        lets through as a ``requests`` error rather than a ``RequestError``.
    """

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.signed: list[tuple[str, str, int]] = []
        self.fail_uploads = False
        self.fail_signing = False
        self.fail_deletes = False

    def client(self, bucket: str, **kwargs: Any) -> FakeGenericRepo:
        return FakeGenericRepo(self, bucket, **kwargs)


class FakeGenericRepo:
    """Implements the ``BKGenericRepo`` methods ``BkRepo`` calls."""

    def __init__(self, server: FakeBkRepoServer, bucket: str, **kwargs: Any) -> None:
        self.server = server
        self.bucket = bucket
        self.project = kwargs["project"]

    def upload_fileobj(self, fh: BinaryIO, key: str, allow_overwrite: bool = True, **kwargs: Any) -> None:
        if self.server.fail_uploads:
            raise UploadFailedError(key=key, src="<fake>")
        self.server.objects[(self.bucket, key)] = fh.read()

    def download_fileobj(self, key: str, fh: BinaryIO, *args: Any, **kwargs: Any) -> None:
        try:
            data = self.server.objects[(self.bucket, key)]
        except KeyError as exc:
            raise DownloadFailedError(key=key, dest="<fake>") from exc
        shutil.copyfileobj(io.BytesIO(data), fh)

    def delete_file(self, key: str, *args: Any, **kwargs: Any) -> None:
        if self.server.fail_deletes:
            raise requests.ConnectionError("connection refused")
        self.server.objects.pop((self.bucket, key), None)

    def generate_presigned_url(self, key: str, expires_in: int, signature_type: Any = None, **kwargs: Any) -> str:
        if self.server.fail_signing:
            raise RequestError("signing refused", code="250101")
        self.server.signed.append((self.bucket, key, expires_in))
        return f"https://bkrepo.example.com/generic/temporary/download/{self.project}/{self.bucket}/{key}?token=t"
