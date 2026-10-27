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

"""Source packages against a real BkRepo: upload, sign, download anonymously, reclaim.

The other source-package tests fake BkRepo under blue_krill's client, so whether the real
service accepts the upload, signs a URL that works without credentials and really deletes the
blob is only checked here. Forgejo stays the in-memory fake, which serves real ``tar.gz``
archives; the live Forgejo tests cover the archive side.

Skipped unless ``BLOBSTORE_BKREPO_CONFIG`` is fully configured, e.g. in ``settings_local.yaml``.
Packages go to ``BLOBSTORE_BUCKET_SOURCE_PACKAGES``, which must already exist.
"""

from __future__ import annotations

import io
import secrets
import tarfile
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from http import HTTPStatus

import pytest
import requests
from blue_krill.storages.blobstore.exceptions import DownloadFailedError, RequestError

from app_spark_api.repository.git import source_packages
from app_spark_api.repository.git.models import ProjectGitRepository, ProjectSourcePackage
from app_spark_api.repository.git.services import provision_project_repository
from app_spark_api.repository.git.source_packages import RepoPackager
from app_spark_api.repository.storage.blob_stores import BkRepo

pytestmark = [pytest.mark.bkrepo, pytest.mark.django_db]

LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)
_REQUIRED_FIELDS = ("PROJECT", "ENDPOINT", "USERNAME", "PASSWORD")


@pytest.fixture
def live_bkrepo(settings) -> Iterator[list[ProjectSourcePackage]]:
    """Skip unless a real BkRepo is configured; delete every blob a test registers afterwards.

    :return: Packages whose blobs are removed at teardown, whatever the test left behind.
    """
    config = settings.BLOBSTORE_BKREPO_CONFIG
    if not isinstance(config, Mapping) or not all(config.get(field) for field in _REQUIRED_FIELDS):
        pytest.skip("BLOBSTORE_BKREPO_CONFIG is not configured")
    if not settings.BLOBSTORE_BUCKET_SOURCE_PACKAGES:
        pytest.skip("BLOBSTORE_BUCKET_SOURCE_PACKAGES is not configured")

    uploaded: list[ProjectSourcePackage] = []
    yield uploaded
    # A blob the test already reclaimed is gone, which counts as deleted.
    for package in uploaded:
        BkRepo(bucket=package.bucket, key=package.key).delete()


@pytest.fixture
def repo(project, fake_forgejo) -> ProjectGitRepository:
    """A repository whose working branch tip holds content unique to this run."""
    repo = provision_project_repository(project)
    head = fake_forgejo.heads[(repo.owner, repo.name)]
    # Keys are already unique per upload; unique content also proves the bytes read back are
    # this run's rather than an older upload's.
    fake_forgejo.trees[head] = {
        "app.py": f"print({secrets.token_hex(8)!r})\n".encode(),
        "templates/index.html": b"<h1>live</h1>\n",
    }
    return repo


def unpack(data: bytes) -> dict[str, bytes]:
    """Regular files in a ``tar.gz`` package, keyed by the path stored in it."""
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile():
                extracted = archive.extractfile(member)
                assert extracted is not None
                files[member.name] = extracted.read()
    return files


def test_a_packaged_commit_downloads_from_its_signed_url_without_credentials(repo, fake_forgejo, live_bkrepo):
    head = fake_forgejo.heads[(repo.owner, repo.name)]
    expected = {f"{repo.name}/{path}": content for path, content in fake_forgejo.trees[head].items()}

    package = RepoPackager(repo).upload()
    live_bkrepo.append(package)

    assert package.commit_sha == head
    stored = BkRepo(bucket=package.bucket, key=package.key).get_bytes()
    assert len(stored) == package.size
    assert unpack(stored) == expected

    url = source_packages.generate_source_package_url(package, expires_in=600)

    # A plain GET with no auth: that is all the release flow fetching the package will have.
    response = requests.get(url, timeout=30)
    assert response.status_code == HTTPStatus.OK, response.text[:500]
    assert response.content == stored

    # Packing the same commit again reuses the uploaded blob instead of uploading another.
    again = RepoPackager(repo).upload()
    assert again.pk == package.pk
    assert again.key == package.key


def test_reclaiming_an_unused_package_deletes_its_blob_from_bkrepo(repo, live_bkrepo):
    package = RepoPackager(repo).upload()
    live_bkrepo.append(package)
    store = BkRepo(bucket=package.bucket, key=package.key)
    assert store.get_bytes(), "the blob must exist before it is reclaimed"
    ProjectSourcePackage.objects.filter(pk=package.pk).update(last_used_at=LONG_AGO)

    reclaimed = source_packages.delete_unused_source_packages()

    assert [p.pk for p in reclaimed.packages] == [package.pk]
    assert reclaimed.orphaned_keys == []
    assert not ProjectSourcePackage.objects.filter(pk=package.pk).exists()
    with pytest.raises(DownloadFailedError):
        store.get_bytes()


def test_deleting_tells_a_blob_already_gone_from_a_refusal(settings, live_bkrepo):
    """The error codes the fake BkRepo copies, checked against the real service."""
    missing_key = f"appspark-src-packages/live-probe/{secrets.token_hex(8)}.tar.gz"
    BkRepo(bucket=settings.BLOBSTORE_BUCKET_SOURCE_PACKAGES, key=missing_key).delete()

    # Also a 404, so only the error code keeps a misconfigured bucket from passing for success.
    with pytest.raises(RequestError) as excinfo:
        BkRepo(bucket=f"app-spark-missing-{secrets.token_hex(4)}", key=missing_key).delete()
    assert str(excinfo.value.code) == "251006"
