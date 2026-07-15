# -*- coding: utf-8 -*-
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

"""Orchestration for archiving volume files to bkrepo and signing download URLs.

The file bytes never pass through apiserver: apiserver only signs short-lived presigned
URLs and tells the resident daemon to archive (daemon reads CFS, computes sha256, and PUTs
directly to bkrepo). Downloads are served by the frontend hitting the signed bkrepo URL.
"""

import logging
from urllib.parse import urlencode, urlparse

from blue_krill.storages.blobstore.base import SignatureType
from django.conf import settings
from django.utils import timezone

from paasng.utils.blobstore import make_blob_store

from .exceptions import SandboxFileNotFound, SandboxFileTooLarge
from .models import Volume, VolumeArtifact
from .resident_daemon_client import ResidentDaemonClient, get_resident_daemon_client

logger = logging.getLogger(__name__)

# 归档 / 下载 URL 的默认与上限有效期(秒)
DEFAULT_DOWNLOAD_URL_EXPIRES_IN = 600
MAX_DOWNLOAD_URL_EXPIRES_IN = 3600
# 上传临时 URL 的有效期,给 daemon 读大文件 + PUT 留足余量
UPLOAD_URL_EXPIRES_IN = 3600


def build_bkrepo_key(volume: Volume, rel_path: str) -> str:
    """Return the bkrepo object key for a volume file.

    Path-addressed (NOT content-addressed): the same rel_path always maps to the same key.
    bkrepo's presigned PUT rejects overwriting an existing node (400 "Node existed"), so
    re-archiving must delete the stale object first (see ``archive_volume_file``). Deduplication
    is handled by VolumeArtifact's (mtime, size) check, since the daemon computes sha256 in a
    single streaming pass and the upload URL must be issued *before* the sha256 is known.
    """
    return f"pv-archives/{volume.application.code}/{volume.uuid.hex}/{rel_path.lstrip('/')}"


def archive_volume_file(volume: Volume, rel_path: str, client: ResidentDaemonClient | None = None) -> VolumeArtifact:
    """Ensure a volume file is archived to bkrepo, returning the (possibly reused) record.

    1. stat the file to obtain (mtime, size); reject files over the size limit.
    2. If a VolumeArtifact exists and its (mtime, size) still matches, reuse it (no re-archive).
    3. Otherwise sign a presigned UPLOAD url, ask the daemon to archive, and upsert the record.

    :raises SandboxFileNotFound: When the file does not exist (propagated from stat).
    :raises SandboxFileTooLarge: When the file exceeds AGENT_SANDBOX_ARTIFACT_MAX_SIZE.
    :raises SandboxArchiveFailed: When the daemon fails to archive.
    """
    client = client or get_resident_daemon_client()
    base_path = volume.storage_path

    meta = client.stat(base_path, rel_path)
    if not meta.get("exists"):
        # 理论上 daemon stat 不存在返回 exists=false; 归一为 not found 交给上层转 404
        raise SandboxFileNotFound(f"file not found: {rel_path}")

    mtime = meta["modified_at"]
    size = meta["size"]
    if size > settings.AGENT_SANDBOX_ARTIFACT_MAX_SIZE:
        raise SandboxFileTooLarge(f"file size {size} exceeds limit {settings.AGENT_SANDBOX_ARTIFACT_MAX_SIZE}")

    existing = VolumeArtifact.objects.filter(volume=volume, rel_path=rel_path).first()
    if existing and existing.is_fresh_for(mtime, size):
        return existing

    key = build_bkrepo_key(volume, rel_path)
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
    # bkrepo 的 presigned PUT 不支持覆盖已存在对象(返回 400 "Node existed"), 重新归档前
    # 先删除旧对象(幂等、容错), 确保 PUT 落在空 key 上。覆盖三类场景:
    # 删除后重建(行已清但对象残留)、内容变更(行陈旧)、宕机竞态(对象存在但无行)。
    delete_bkrepo_object(store, key)
    upload_url = store.generate_presigned_url(
        key=key, expires_in=UPLOAD_URL_EXPIRES_IN, signature_type=SignatureType.UPLOAD
    )

    result = client.archive(base_path, rel_path, upload_url)

    artifact, _ = VolumeArtifact.objects.update_or_create(
        volume=volume,
        rel_path=rel_path,
        defaults={
            "mtime": result.get("mtime", mtime),
            "size": result.get("size", size),
            "sha256": result["sha256"],
            "bkrepo_key": key,
            "archived_at": timezone.now(),
            "tenant_id": volume.tenant_id,
        },
    )
    return artifact


def delete_bkrepo_object(store, key: str) -> None:
    """Best-effort deletion of a bkrepo object.

    Tolerates a missing object or any backend failure (logged, not raised): a leftover or
    failing delete must not abort the caller's flow — the next archive re-creates the object,
    and a file deletion has already removed the CFS file.
    """
    try:
        store.delete_file(key)
    except Exception:
        logger.exception("Failed to delete bkrepo object (key=%s); ignoring", key)


def delete_volume_artifact(volume: Volume, rel_path: str) -> None:
    """Delete the bkrepo object + dedup row for a volume file (inverse of archive).

    Best-effort on the bkrepo side: a missing or failing object delete does not abort the file
    deletion. The dedup row is always cleared so the next archive re-uploads rather than
    reusing a stale mapping that points at a (possibly gone) object.
    """
    artifact = VolumeArtifact.objects.filter(volume=volume, rel_path=rel_path).first()
    if not artifact:
        return
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
    delete_bkrepo_object(store, artifact.bkrepo_key)
    artifact.delete()


def build_download_urls(artifact: VolumeArtifact, expires_in: int) -> tuple[str, str]:
    """Sign a single presigned DOWNLOAD url and derive two mutually-exclusive URLs from it.

    Both URLs share the same presigned base + signature and differ only by the trailing
    flag query: ``download_url`` carries ``download=true`` (attachment), ``preview_url``
    carries ``preview=true`` (inline preview). Each URL only carries its own flag, so the
    two are independent and mutually exclusive.

    Note: bkrepo's generic download only honours the ``download`` param; ``preview=true``
    is the agreed literal with the gateway/frontend and must be interpreted upstream.
    """
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
    url = store.generate_presigned_url(
        key=artifact.bkrepo_key, expires_in=expires_in, signature_type=SignatureType.DOWNLOAD
    )
    sep = "&" if urlparse(url).query else "?"
    download_url = f"{url}{sep}{urlencode({'download': 'true'})}"
    preview_url = f"{url}{sep}{urlencode({'preview': 'true'})}"
    return download_url, preview_url
