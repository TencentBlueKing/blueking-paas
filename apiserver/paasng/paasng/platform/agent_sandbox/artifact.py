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

from blue_krill.storages.blobstore.base import SignatureType
from django.conf import settings
from django.utils import timezone

from paasng.utils.blobstore import BlobStore, make_blob_store

from .constants import UPLOAD_URL_EXPIRES_IN
from .exceptions import SandboxFileNotFound
from .models import Volume, VolumeArtifact
from .resident_daemon_client import ResidentDaemonClient, get_resident_daemon_client

logger = logging.getLogger(__name__)


def build_bkrepo_key(volume: Volume, rel_path: str) -> str:
    """Return the bkrepo object key for a volume file.

    Path-addressed (NOT content-addressed): the same rel_path always maps to the same key.
    bkrepo's presigned PUT rejects overwriting an existing node (400 "Node existed"), so
    re-archiving must delete the stale object first (see ``archive_volume_file``). Deduplication
    is handled by VolumeArtifact's (mtime, size) check, since the daemon computes sha256 in a
    single streaming pass and the upload URL must be issued *before* the sha256 is known.

    :param rel_path: relative path of the file within the volume (e.g. "foo/bar.txt")
    """
    return f"pv-archives/{volume.application.code}/{volume.uuid.hex}/{rel_path.lstrip('/')}"


def archive_volume_file(volume: Volume, rel_path: str, client: ResidentDaemonClient | None = None) -> VolumeArtifact:
    """Ensure a volume file is archived to bkrepo, returning the (possibly reused) record.

    1. stat the file to obtain (mtime, size); reject files over the size limit.
    2. If a VolumeArtifact exists and its (mtime, size) still matches, reuse it (no re-archive).
    3. Otherwise sign a presigned UPLOAD url, ask the daemon to archive, and upsert the record.

    :raises SandboxFileNotFound: When the file does not exist (propagated from stat).
    :raises SandboxFileTooLarge: When the file exceeds deamon limits
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

    existing = VolumeArtifact.objects.filter(volume=volume, rel_path=rel_path).first()
    # volume + relative path + mtime + size 都相同才可能复用已归档对象
    if existing and existing.is_fresh_for(mtime, size):
        return existing

    key = build_bkrepo_key(volume, rel_path)
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)

    if existing:
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


def delete_bkrepo_object(store: BlobStore, key: str) -> None:
    try:
        store.delete_file(key)
    except Exception:
        logger.exception("Failed to delete bkrepo object (key=%s); ignoring", key)


def delete_volume_artifact(volume: Volume, rel_path: str) -> None:
    """
    Delete the bkrepo object & dedup row for a volume file (inverse of archive).
    """
    artifact = VolumeArtifact.objects.filter(volume=volume, rel_path=rel_path).first()
    if not artifact:
        return
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
    delete_bkrepo_object(store, artifact.bkrepo_key)
    artifact.delete()


def build_download_url(artifact: VolumeArtifact, expires_in: int) -> str:
    """
    Sign a single presigned DOWNLOAD url.
    """
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
    return store.generate_presigned_url(
        key=artifact.bkrepo_key, expires_in=expires_in, signature_type=SignatureType.DOWNLOAD
    )
