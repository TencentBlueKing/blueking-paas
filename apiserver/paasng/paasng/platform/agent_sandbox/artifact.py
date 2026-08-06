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

from urllib.parse import quote, urlencode

from blue_krill.storages.blobstore.base import SignatureType
from blue_krill.storages.blobstore.bkrepo import TIMEOUT_THRESHOLD, BKGenericRepo, safe_urljoin
from blue_krill.storages.blobstore.exceptions import RequestError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from paasng.utils.blobstore import make_blob_store

from .constants import PREVIEW_EXTRA_PARAM, PREVIEW_REPO_TYPE, PREVIEW_TOKEN_TYPE, UPLOAD_URL_EXPIRES_IN
from .exceptions import SandboxFileNotFound
from .models import Volume, VolumeArtifact
from .resident_daemon_client import ResidentDaemonClient, get_resident_daemon_client


def build_bkrepo_key(volume: Volume, rel_path: str) -> str:
    """Build the path-addressed bkrepo key for a volume file."""
    return f"pv-archives/{volume.application.code}/{volume.uuid.hex}/{rel_path.lstrip('/')}"


def archive_volume_file(volume: Volume, rel_path: str, client: ResidentDaemonClient | None = None) -> VolumeArtifact:
    """Ensure a volume file is archived to bkrepo, returning the (possibly reused) record.

    :raises SandboxFileNotFound: When the file does not exist (propagated from stat).
    :raises SandboxFileTooLarge: When the file exceeds daemon limits.
    :raises SandboxArchiveFailed: When the daemon fails to archive.
    """
    client = client or get_resident_daemon_client()
    base_path = volume.storage_path

    meta = client.stat(base_path, rel_path)
    if not meta.get("exists"):
        raise SandboxFileNotFound(f"file not found: {rel_path}")

    mtime = meta["modified_at"]
    size = meta["size"]

    existing = VolumeArtifact.objects.filter(volume=volume, rel_path=rel_path).first()
    if existing and existing.is_fresh_for(mtime, size):
        return existing

    key = build_bkrepo_key(volume, rel_path)
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)

    if existing:
        store.delete_file(key)

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


def delete_volume_artifact(volume: Volume, rel_path: str) -> None:
    """Delete the archived object and its volume-file mapping."""
    artifact = VolumeArtifact.objects.filter(volume=volume, rel_path=rel_path).first()
    if not artifact:
        return
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
    store.delete_file(artifact.bkrepo_key)
    artifact.delete()


def build_download_url(artifact: VolumeArtifact, expires_in: int) -> str:
    """Sign a download URL for an archived object."""
    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
    return store.generate_presigned_url(
        key=artifact.bkrepo_key, expires_in=expires_in, signature_type=SignatureType.DOWNLOAD
    )


def build_preview_url(artifact: VolumeArtifact, expires_in: int) -> str:
    """Build a bkrepo web preview page URL for an archived object.

    Unlike :func:`build_download_url`, this is *not* a presigned object URL — it points at
    bkrepo's frontend preview route, which renders the file (images, PDF, ...) in a page:

        {BK_REPO_URL}/ui/{project}/filePreview/local/0/{repo}/{key}?token={token}

    The token must be created with type ``PREVIEW``; bkrepo's preview service rejects
    ``DOWNLOAD`` tokens, so ``generate_presigned_url`` cannot be reused here.

    :raises ImproperlyConfigured: When ``BK_REPO_URL`` is not configured, or the artifact
        bucket is not backed by bkrepo (preview is a bkrepo-only capability).
    """
    if not settings.BK_REPO_URL:
        raise ImproperlyConfigured('"BK_REPO_URL" is required to build bkrepo preview URLs')

    store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
    if not isinstance(store, BKGenericRepo):
        raise ImproperlyConfigured(f"preview URL is only supported by bkrepo, not {type(store).__name__}")

    token = create_preview_token(store, artifact.bkrepo_key, expires_in)
    # key 内含用户可控的文件名，逐段转义；"/" 是路由分隔符，需保留
    quoted_key = quote(artifact.bkrepo_key, safe="/")
    return (
        f"{settings.BK_REPO_URL.rstrip('/')}/ui/{store.project}/filePreview"
        f"/{PREVIEW_REPO_TYPE}/{PREVIEW_EXTRA_PARAM}/{store.bucket}/{quoted_key}"
        f"?{urlencode({'token': token})}"
    )


def create_preview_token(store: BKGenericRepo, key: str, expires_in: int) -> str:
    """Create a bkrepo temporary token of type ``PREVIEW`` for a single object.

    :param expires_in: Token lifetime in seconds; ``<= 0`` means never expires.
    :raises RequestError: When bkrepo rejects the request or returns no token.
    """
    url = safe_urljoin(store.endpoint_url, "generic/temporary/token/create")
    resp = store.get_client().post(
        url,
        json={
            "projectId": store.project,
            "repoName": store.bucket,
            "fullPathSet": [f"/{key.lstrip('/')}"],
            "expireSeconds": expires_in,
            "type": PREVIEW_TOKEN_TYPE,
        },
        timeout=TIMEOUT_THRESHOLD,
    )
    try:
        data = resp.json()
    except ValueError as e:
        raise RequestError(str(e), code="Unknown", response=resp) from e
    if data.get("code") != 0:
        raise RequestError(data.get("message"), code=str(data.get("code")), response=resp)

    tokens = data.get("data") or []
    if not tokens:
        raise RequestError("bkrepo returned no preview token", code=str(data.get("code")), response=resp)
    return tokens[0]["token"]
