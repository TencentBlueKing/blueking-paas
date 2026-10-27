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

"""Packing a Project's source at one commit into BkRepo, for a release to fetch.

Two operations, kept apart on purpose:

* :meth:`RepoPackager.upload` resolves the working branch or a tag to a commit, packs that
  commit and records it. It is slow -- an archive download and an upload -- but it happens
  once per commit, and its result is reused until it is reclaimed.
* :func:`generate_source_package_url` signs a download URL for a recorded package. It is cheap
  and is meant to be called whenever a release needs a URL, because the URL expires while the
  package does not.

Packages are not kept forever. Both operations above mark a package as used, and
:func:`delete_unused_source_packages` (run by the ``delete_unused_source_packages`` command)
removes those nobody has used for a while.

Example::

    package = RepoPackager(repo).upload(tag="v1.0.0")
    url = generate_source_package_url(package)
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import attrs
from asgiref.sync import sync_to_async
from blue_krill.storages.blobstore.exceptions import RequestError, UploadFailedError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from app_spark_api.repository.git.exceptions import (
    GitRepositoryNotReadyError,
    SourcePackageError,
    SourceRefNotFoundError,
)
from app_spark_api.repository.git.factory import make_forgejo_client
from app_spark_api.repository.git.models import ProjectSourcePackage
from app_spark_api.repository.storage.blob_stores import BkRepo
from app_spark_api.repository.storage.utils import generate_temp_file

if TYPE_CHECKING:
    from app_spark_api.infras.forgejo.client import ForgejoClient
    from app_spark_api.repository.git.models import ProjectGitRepository

SOURCE_PACKAGE_SUFFIX = "tar.gz"
# A release may sit in a build queue before it fetches the package, so the URL has to outlive
# that wait. One day matches what the PaaS platform signs for its own source packages.
DEFAULT_URL_EXPIRES_IN = 24 * 60 * 60
# The longest URL lifetime that may be signed. Reclamation must wait longer than this after a
# package's last use, so that no URL handed out can outlive the package it points at.
MAX_URL_EXPIRES_IN = 7 * 24 * 60 * 60
# How long a package may go unused before the cleanup command reclaims it.
DEFAULT_UNUSED_FOR = timedelta(days=15)

# Keeps the packages from colliding with anything else stored in the same bucket.
_BK_REPO_KEY_PREFIX = "appspark-src-packages"
# Characters `git check-ref-format` forbids anywhere in a ref name.
_FORBIDDEN_REF_CHARACTERS = re.compile(r"[\x00-\x20\x7f~^:?*\[\\]")

logger = logging.getLogger(__name__)


class RepoPackager:
    """Packs one Project repository's commits into BkRepo and records each package.

    Example::

        packager = RepoPackager(repo)
        package = packager.upload()  # tip of the working branch
        package = packager.upload(tag="v1.0.0")

    :param repo: The repository row to pack from.
    :param client: Injected Forgejo client, which the caller keeps ownership of; production
        builds one per upload from settings.
    """

    def __init__(self, repo: ProjectGitRepository, *, client: ForgejoClient | None = None) -> None:
        self.repo = repo
        self._client = client

    def upload(self, tag: str | None = None) -> ProjectSourcePackage:
        """Pack the repository at ``tag``, or at its working branch's tip, and upload it to BkRepo.

        The package is Forgejo's ``tar.gz`` archive of the commit, uploaded unchanged: the source
        tree nested under one directory named after the repository, e.g. ``{repo}/app.py``, and
        no Git metadata. It is not repacked to lift the files to the root, because the Developer
        Center accepts a package whose source sits in a single subdirectory.

        A commit that has been packed before is not packed again: its existing record is marked
        used and returned, because a commit's content cannot change. So re-releasing the working
        branch uploads only when something has been pushed since, or the old package has been
        reclaimed.

        The ref is resolved to a commit first and the archive is cut from that commit rather
        than from the ref's name, so a push landing halfway through cannot pack a different
        commit from the one recorded.

        :param tag: Tag to pack. ``None`` packs the current tip of ``repo.default_branch``.
        :return: The record of the uploaded, or previously uploaded, package.
        :raises GitRepositoryNotReadyError: The remote repository does not exist yet.
        :raises SourceRefNotFoundError: ``tag`` is not a tag of the repository.
        :raises SourcePackageError: The archive could not be uploaded, or a concurrent upload of
            the same commit won and its package was reclaimed before it could be reused.
        :raises django.core.exceptions.ImproperlyConfigured: ``BLOBSTORE_BKREPO_CONFIG`` is
            missing or incomplete.
        :raises app_spark_api.infras.forgejo.exceptions.ForgejoError: Forgejo was unreachable
            or refused a read.
        """
        repo = self.repo
        if not repo.has_remote_repository:
            raise GitRepositoryNotReadyError(f"Project {repo.project_id} has no remote Git repository yet")
        if tag is not None and not self._is_valid_tag_name(tag):
            raise SourceRefNotFoundError(f"{tag!r} is not a valid tag name")

        forgejo = self._client or make_forgejo_client()
        try:
            commit = self._resolve_commit(forgejo, tag)
            existing = ProjectSourcePackage.objects.filter(project_id=repo.project_id, commit_sha=commit).first()
            # Failing to mark it means reclamation deleted it just now, so pack it again.
            if existing is not None and existing.mark_used():
                return existing

            bucket = settings.BLOBSTORE_BUCKET_SOURCE_PACKAGES
            key = self._new_key(commit)
            # Built before the download so a missing BkRepo configuration fails before any work.
            store = BkRepo(bucket=bucket, key=key)
            with generate_temp_file(suffix=f".{SOURCE_PACKAGE_SUFFIX}") as package_path:
                with package_path.open("wb") as handle:
                    forgejo.download_archive(
                        owner=repo.owner, name=repo.name, ref=commit, suffix=SOURCE_PACKAGE_SUFFIX, handle=handle
                    )
                size = package_path.stat().st_size
                try:
                    store.put(package_path)
                except UploadFailedError as exc:
                    raise SourcePackageError(
                        f"Uploading the source package of {repo.project_id}@{commit} failed"
                    ) from exc
        finally:
            if self._client is None:
                forgejo.close()

        try:
            package, created = ProjectSourcePackage.objects.get_or_create(
                project_id=repo.project_id,
                commit_sha=commit,
                defaults={
                    "repo_full_name": f"{repo.owner}/{repo.name}",
                    "bucket": bucket,
                    "key": key,
                    "size": size,
                    "tenant_id": repo.project.tenant_id,
                },
            )
        except Exception:
            # No row records the blob just uploaded, so reclamation would never find it.
            _delete_blob(store)
            raise
        if not created:
            # A concurrent release of the same commit recorded its upload first. Its row stands,
            # so the blob uploaded here is referenced by nothing and would never be reclaimed.
            _delete_blob(store)
            if not package.mark_used():
                # Reclamation deleted that row in between, so no blob is left to hand out.
                raise SourcePackageError(
                    f"The source package of {repo.project_id}@{commit} was reclaimed while being recorded; "
                    "upload it again"
                )
        return package

    async def aupload(self, tag: str | None = None) -> ProjectSourcePackage:
        """Async wrapper for :meth:`upload`."""
        return await sync_to_async(self.upload)(tag)

    def _new_key(self, commit_sha: str) -> str:
        """Return a fresh BkRepo object key for one upload of ``commit_sha``.

        加入 UUID 为每次都生成唯一的 key，即使相同的 SHA 也不会复用地址。

        :return: An object key such as ``appspark-src-packages/demo/3f2a.../9c1e....tar.gz``.
        """
        return f"{_BK_REPO_KEY_PREFIX}/{self.repo.project_id}/{commit_sha}/{uuid4().hex}.{SOURCE_PACKAGE_SUFFIX}"

    def _resolve_commit(self, forgejo: ForgejoClient, tag: str | None) -> str:
        repo = self.repo
        if tag is None:
            return forgejo.get_branch(repo.owner, repo.name, repo.default_branch).commit
        remote_tag = forgejo.get_tag(repo.owner, repo.name, tag)
        if remote_tag is None:
            raise SourceRefNotFoundError(f"Project {repo.project_id} has no tag {tag!r}")
        return remote_tag.commit

    @staticmethod
    def _is_valid_tag_name(tag: str) -> bool:
        """Whether ``tag`` could name a Git tag, following the rules of ``git check-ref-format``.

        Checked before the name is put in a URL: Forgejo would answer "not found" for most
        invalid names anyway, but a name made of ``..`` segments would resolve to a different
        API route.
        """
        if not tag or tag == "@" or _FORBIDDEN_REF_CHARACTERS.search(tag):
            return False
        if ".." in tag or "@{" in tag or tag.endswith("."):
            return False
        # Every slash-separated component must be non-empty, not start with a dot, and not end
        # with `.lock`; e.g. `release/v1` is fine, `release//v1` and `.hidden` are not.
        return all(part and not part.startswith(".") and not part.endswith(".lock") for part in tag.split("/"))


def generate_source_package_url(package: ProjectSourcePackage, *, expires_in: int = DEFAULT_URL_EXPIRES_IN) -> str:
    """Sign a URL the package can be downloaded from without BkRepo credentials.

    Signing marks the package used, which keeps it from being reclaimed while the URL is valid.

    :param package: A recorded package, from :meth:`RepoPackager.upload`.
    :param expires_in: Lifetime of the URL in seconds, at most :data:`MAX_URL_EXPIRES_IN`.
    :return: The signed download URL.
    :raises ValueError: If ``expires_in`` is not positive or exceeds the maximum.
    :raises SourcePackageError: The package has been reclaimed, which calls for uploading it
        again, or BkRepo could not be reached or refused to sign.
    :raises django.core.exceptions.ImproperlyConfigured: ``BLOBSTORE_BKREPO_CONFIG`` is missing
        or incomplete.
    """
    if not 0 < expires_in <= MAX_URL_EXPIRES_IN:
        raise ValueError(f"expires_in must be within (0, {MAX_URL_EXPIRES_IN}], got {expires_in}")
    store = BkRepo(bucket=package.bucket, key=package.key)
    if not package.mark_used():
        raise SourcePackageError(f"The source package {package.key} has been reclaimed; upload it again")
    try:
        return store.generate_presigned_url(expires_in)
    # `requests`' own failures (a refused connection, a timeout) derive from OSError, and
    # blue_krill lets them through unwrapped.
    except (RequestError, OSError) as exc:
        raise SourcePackageError(f"Signing a download URL for {package.key} failed") from exc


async def agenerate_source_package_url(
    package: ProjectSourcePackage, *, expires_in: int = DEFAULT_URL_EXPIRES_IN
) -> str:
    """Async wrapper for :func:`generate_source_package_url`."""
    return await sync_to_async(generate_source_package_url)(package, expires_in=expires_in)


@attrs.frozen
class Reclaimed:
    """What one reclamation run removed.

    :param packages: Packages whose rows were deleted, or would be under ``dry_run``.
    :param orphaned_keys: Keys of blobs whose rows are gone but which could not be deleted.
        Nothing references them any more, so they only cost storage; operators may remove them
        from BkRepo by hand.
    """

    packages: list[ProjectSourcePackage]
    orphaned_keys: list[str]


def delete_unused_source_packages(unused_for: timedelta = DEFAULT_UNUSED_FOR, *, dry_run: bool = False) -> Reclaimed:
    """Delete every package nobody has used for ``unused_for``, both its row and its blob.

    Row first, then blob, the same order context versions are reclaimed in. The other way
    round, a failed row delete would leave a record whose blob is gone, and a release reusing
    it would fail. An orphaned blob only costs storage.

    Each row is re-checked under a lock as it is deleted: a release may reuse a package after
    it was listed here, and once that release has marked it used it must keep its blob.

    Example::

        reclaimed = delete_unused_source_packages(timedelta(days=30), dry_run=True)

    :param unused_for: How long a package must have gone unused. Must exceed
        :data:`MAX_URL_EXPIRES_IN`, so that no signed URL outlives its package.
    :param dry_run: Only report what would be deleted.
    :return: What was deleted, and which blobs could not be.
    :raises ValueError: If ``unused_for`` does not exceed the longest URL lifetime.
    :raises django.core.exceptions.ImproperlyConfigured: ``BLOBSTORE_BKREPO_CONFIG`` is missing
        or incomplete. Raised before any row is deleted.
    """
    if unused_for <= timedelta(seconds=MAX_URL_EXPIRES_IN):
        raise ValueError(f"unused_for must exceed the longest URL lifetime of {MAX_URL_EXPIRES_IN} seconds")

    cutoff = timezone.now() - unused_for
    candidates = list(ProjectSourcePackage.objects.unused_since(cutoff).order_by("last_used_at", "pk"))
    if dry_run:
        return Reclaimed(packages=candidates, orphaned_keys=[])

    deleted: list[ProjectSourcePackage] = []
    orphaned_keys: list[str] = []
    for package in candidates:
        # Built before the row goes, so a missing configuration stops the run instead of
        # deleting every row and orphaning every blob.
        store = BkRepo(bucket=package.bucket, key=package.key)
        with transaction.atomic():
            locked = (
                ProjectSourcePackage.objects.select_for_update().unused_since(cutoff).filter(pk=package.pk).first()
            )
            if locked is None:
                continue
            locked.delete()
        deleted.append(package)
        if not _delete_blob(store):
            orphaned_keys.append(package.key)

    logger.info("Reclaimed %d source package(s) unused since %s", len(deleted), cutoff.isoformat())
    return Reclaimed(packages=deleted, orphaned_keys=orphaned_keys)


def _delete_blob(store: BkRepo) -> bool:
    """Delete a blob nothing references any more, logging rather than raising on failure."""
    try:
        store.delete()
    except Exception:
        # Every failure is handled the same way: no row points here, so the blob only costs storage.
        logger.exception("Could not delete the source package blob at %s", store.key)
        return False
    return True
