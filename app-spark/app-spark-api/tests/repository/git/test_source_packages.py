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

"""Packing a commit into BkRepo, and signing where a release can fetch it from.

Forgejo is the in-memory fake and BkRepo is faked under blue_krill's client; the live Forgejo
tests are what check the layout of a real archive.
"""

from __future__ import annotations

import io
import tarfile
from datetime import UTC, datetime
from http import HTTPStatus

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError

from app_spark_api.infras.forgejo import ForgejoClient
from app_spark_api.infras.forgejo.exceptions import ForgejoUnavailableError
from app_spark_api.repository.git import source_packages
from app_spark_api.repository.git.exceptions import (
    GitRepositoryNotReadyError,
    SourcePackageError,
    SourceRefNotFoundError,
)
from app_spark_api.repository.git.models import ProjectSourcePackage
from app_spark_api.repository.git.services import provision_project_repository
from app_spark_api.repository.git.source_packages import RepoPackager
from tests.infras.forgejo.fake import DEFAULT_TREE

pytestmark = pytest.mark.django_db

BUCKET = "app-spark-source-packages"
LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)
TAGGED_COMMIT = "7a9" + "0" * 37
TAGGED_TREE = {"app.py": b"print('v1')\n", "templates/index.html": b"<h1>v1</h1>\n"}


@pytest.fixture
def repo(project, fake_forgejo):
    return provision_project_repository(project)


@pytest.fixture
def head(repo, fake_forgejo):
    """SHA the working branch is at, which is what a release without a tag packs."""
    return fake_forgejo.heads[(repo.owner, repo.name)]


def package_files(fake_bkrepo, package: ProjectSourcePackage) -> dict[str, bytes]:
    """Unpack a stored package, keyed by the path stored in it, e.g. ``{repo}/README.md``."""
    data = fake_bkrepo.objects[(package.bucket, package.key)]
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile():
                extracted = archive.extractfile(member)
                assert extracted is not None
                files[member.name] = extracted.read()
    return files


def in_repo_dir(repo, tree: dict[str, bytes]) -> dict[str, bytes]:
    """``tree`` as Forgejo archives it: nested under a directory named after the repository."""
    return {f"{repo.name}/{path}": content for path, content in tree.items()}


class TestUploadSourcePackage:
    def test_without_a_tag_the_working_branch_tip_is_packed(self, repo, head, fake_bkrepo):
        package = RepoPackager(repo).upload()

        assert package.commit_sha == head
        assert package.project_id == repo.project_id
        assert package.tenant_id == repo.project.tenant_id
        assert package.repo_full_name == f"{repo.owner}/{repo.name}"
        assert package.bucket == BUCKET
        assert package.key.startswith(f"appspark-src-packages/{repo.project_id}/{head}/")
        assert package.key.endswith(".tar.gz")
        assert package.size == len(fake_bkrepo.objects[(BUCKET, package.key)])
        # Uploaded as Forgejo archived it; the Developer Center takes the source from the subdirectory.
        assert package_files(fake_bkrepo, package) == in_repo_dir(repo, DEFAULT_TREE)

    def test_a_tag_packs_the_commit_it_points_at(self, repo, head, fake_forgejo, fake_bkrepo):
        fake_forgejo.tags[(repo.owner, repo.name)] = {"v1.0.0": TAGGED_COMMIT}
        fake_forgejo.trees[TAGGED_COMMIT] = TAGGED_TREE

        package = RepoPackager(repo).upload(tag="v1.0.0")

        assert package.commit_sha == TAGGED_COMMIT
        assert package_files(fake_bkrepo, package) == in_repo_dir(repo, TAGGED_TREE)
        # Cut from the commit rather than the name, so a push in between cannot change it.
        assert fake_forgejo.archive_requests == [f"{TAGGED_COMMIT}.tar.gz"]

    def test_a_tag_with_a_slash_is_found(self, repo, fake_forgejo, fake_bkrepo):
        fake_forgejo.tags[(repo.owner, repo.name)] = {"release/v1": TAGGED_COMMIT}

        package = RepoPackager(repo).upload(tag="release/v1")

        assert package.commit_sha == TAGGED_COMMIT

    def test_the_same_commit_is_uploaded_once(self, repo, head, fake_forgejo, fake_bkrepo):
        first = RepoPackager(repo).upload()
        ProjectSourcePackage.objects.filter(pk=first.pk).update(last_used_at=LONG_AGO)
        # Reached through a tag this time, but it is the same commit, so the same content.
        fake_forgejo.tags[(repo.owner, repo.name)] = {"v1.0.0": head}
        fake_bkrepo.fail_uploads = True

        second = RepoPackager(repo).upload(tag="v1.0.0")

        assert second.pk == first.pk
        assert fake_forgejo.archive_requests == [f"{head}.tar.gz"]
        assert ProjectSourcePackage.objects.filter(project=repo.project).count() == 1
        # Reuse counts as use, so a package released again is not reclaimed.
        assert ProjectSourcePackage.objects.get(pk=first.pk).last_used_at > LONG_AGO

    def test_a_package_reclaimed_while_being_reused_is_packed_again(self, repo, head, fake_bkrepo, monkeypatch):
        first = RepoPackager(repo).upload()
        mark_used = ProjectSourcePackage.mark_used

        def reclaimed_first(package):
            # Reclamation wins the row lock between the lookup and the mark.
            ProjectSourcePackage.objects.filter(pk=package.pk).delete()
            monkeypatch.setattr(ProjectSourcePackage, "mark_used", mark_used)
            return mark_used(package)

        monkeypatch.setattr(ProjectSourcePackage, "mark_used", reclaimed_first)

        second = RepoPackager(repo).upload()

        assert second.pk != first.pk
        assert second.commit_sha == head
        # A fresh key, so the reclaimer's late delete of the old blob cannot reach this one.
        assert second.key != first.key
        assert package_files(fake_bkrepo, second) == in_repo_dir(repo, DEFAULT_TREE)

    def test_losing_a_race_to_record_the_same_commit_discards_this_upload(self, repo, head, fake_bkrepo, monkeypatch):
        download_archive = ForgejoClient.download_archive

        def concurrent_release_records_first(client, **kwargs):
            download_archive(client, **kwargs)
            ProjectSourcePackage.objects.create(
                project=repo.project,
                repo_full_name=f"{repo.owner}/{repo.name}",
                commit_sha=kwargs["ref"],
                bucket=BUCKET,
                key="appspark-src-packages/winner.tar.gz",
                size=1,
            )

        monkeypatch.setattr(ForgejoClient, "download_archive", concurrent_release_records_first)

        package = RepoPackager(repo).upload()

        assert package.key == "appspark-src-packages/winner.tar.gz"
        # The loser's blob is referenced by no row, so nothing would ever reclaim it.
        assert fake_bkrepo.objects == {}

    def test_a_winner_reclaimed_before_the_loser_reuses_it_is_an_error(self, repo, fake_bkrepo, monkeypatch):
        download_archive = ForgejoClient.download_archive
        mark_used = ProjectSourcePackage.mark_used

        def concurrent_release_records_first(client, **kwargs):
            download_archive(client, **kwargs)
            ProjectSourcePackage.objects.create(
                project=repo.project,
                repo_full_name=f"{repo.owner}/{repo.name}",
                commit_sha=kwargs["ref"],
                bucket=BUCKET,
                key="appspark-src-packages/winner.tar.gz",
                size=1,
            )

        def reclaimed_first(package):
            ProjectSourcePackage.objects.filter(pk=package.pk).delete()
            return mark_used(package)

        monkeypatch.setattr(ForgejoClient, "download_archive", concurrent_release_records_first)
        monkeypatch.setattr(ProjectSourcePackage, "mark_used", reclaimed_first)

        with pytest.raises(SourcePackageError, match="reclaimed while being recorded"):
            RepoPackager(repo).upload()

        assert not ProjectSourcePackage.objects.exists()
        assert fake_bkrepo.objects == {}

    def test_a_failure_recording_the_upload_deletes_its_blob(self, repo, fake_bkrepo, monkeypatch):
        def database_down(**kwargs):
            raise DatabaseError("connection lost")

        monkeypatch.setattr(ProjectSourcePackage.objects, "get_or_create", database_down)

        with pytest.raises(DatabaseError):
            RepoPackager(repo).upload()

        # Nothing records the blob, so reclamation would never find it.
        assert fake_bkrepo.objects == {}

    def test_each_new_tip_of_the_working_branch_gets_its_own_package(self, repo, head, fake_forgejo, fake_bkrepo):
        """The working branch is released over and over; only the SHA tells the versions apart."""
        first = RepoPackager(repo).upload()
        pushed = "b0b" + "0" * 37
        fake_forgejo.heads[(repo.owner, repo.name)] = pushed
        fake_forgejo.trees[pushed] = {"README.md": b"# pushed\n"}

        second = RepoPackager(repo).upload()

        assert (first.commit_sha, second.commit_sha) == (head, pushed)
        assert first.key != second.key
        assert package_files(fake_bkrepo, first) == in_repo_dir(repo, DEFAULT_TREE)
        assert package_files(fake_bkrepo, second) == in_repo_dir(repo, {"README.md": b"# pushed\n"})
        assert ProjectSourcePackage.objects.filter(project=repo.project).count() == 2

    def test_an_unknown_tag_is_refused(self, repo, fake_bkrepo):
        with pytest.raises(SourceRefNotFoundError, match="no tag 'v9'"):
            RepoPackager(repo).upload(tag="v9")

        assert not ProjectSourcePackage.objects.exists()

    @pytest.mark.parametrize("tag", ["", "..", "../../x", "a..b", ".hidden", "v1/", "a//b", "a b", "v1.lock", "a@{1}"])
    def test_a_name_that_cannot_be_a_tag_never_reaches_forgejo(self, repo, fake_forgejo, fake_bkrepo, tag):
        fake_forgejo.fail_next_request = True

        with pytest.raises(SourceRefNotFoundError, match="not a valid tag name"):
            RepoPackager(repo).upload(tag=tag)

        assert fake_forgejo.fail_next_request, "the name must be refused before any request"

    def test_a_repository_without_a_remote_is_refused(self, repo, fake_bkrepo):
        repo.remote_id = None

        with pytest.raises(GitRepositoryNotReadyError):
            RepoPackager(repo).upload()

    def test_missing_bkrepo_configuration_fails_before_downloading(self, repo, fake_forgejo, settings):
        settings.BLOBSTORE_BKREPO_CONFIG = None

        with pytest.raises(ImproperlyConfigured, match="BLOBSTORE_BKREPO_CONFIG"):
            RepoPackager(repo).upload()

        assert fake_forgejo.archive_requests == []

    def test_a_failed_upload_records_nothing(self, repo, fake_bkrepo):
        fake_bkrepo.fail_uploads = True

        with pytest.raises(SourcePackageError, match="Uploading the source package"):
            RepoPackager(repo).upload()

        assert not ProjectSourcePackage.objects.exists()

    def test_a_failed_archive_download_records_nothing(self, repo, fake_forgejo, fake_bkrepo):
        fake_forgejo.archive_status = HTTPStatus.INTERNAL_SERVER_ERROR

        with pytest.raises(ForgejoUnavailableError, match="GET archive"):
            RepoPackager(repo).upload()

        assert fake_bkrepo.objects == {}
        assert not ProjectSourcePackage.objects.exists()

    # The wrapper runs the ORM on another thread, which only sees committed rows.
    @pytest.mark.django_db(transaction=True)
    async def test_the_async_wrapper_packs_the_same_way(self, repo, head, fake_bkrepo):
        package = await RepoPackager(repo).aupload()

        assert package.commit_sha == head


class TestGenerateSourcePackageUrl:
    @pytest.fixture
    def package(self, repo, fake_bkrepo):
        return RepoPackager(repo).upload()

    def test_a_download_url_is_signed_for_the_stored_object(self, package, fake_bkrepo):
        url = source_packages.generate_source_package_url(package)

        assert url.startswith("https://bkrepo.example.com/generic/temporary/download/")
        assert fake_bkrepo.signed == [(package.bucket, package.key, source_packages.DEFAULT_URL_EXPIRES_IN)]

    def test_the_lifetime_can_be_chosen(self, package, fake_bkrepo):
        source_packages.generate_source_package_url(package, expires_in=600)

        assert fake_bkrepo.signed[-1][2] == 600

    @pytest.mark.parametrize("expires_in", [0, -1, source_packages.MAX_URL_EXPIRES_IN + 1])
    def test_a_url_outliving_the_retention_guarantee_is_refused(self, package, fake_bkrepo, expires_in):
        """BkRepo reads `<= 0` as "forever"; and a URL longer than the maximum could outlive its package."""
        with pytest.raises(ValueError, match="expires_in must be within"):
            source_packages.generate_source_package_url(package, expires_in=expires_in)

        assert fake_bkrepo.signed == []

    def test_signing_marks_the_package_used(self, package, fake_bkrepo):
        ProjectSourcePackage.objects.filter(pk=package.pk).update(last_used_at=LONG_AGO)

        source_packages.generate_source_package_url(package)

        assert ProjectSourcePackage.objects.get(pk=package.pk).last_used_at > LONG_AGO

    def test_a_reclaimed_package_is_not_signed(self, package, fake_bkrepo):
        ProjectSourcePackage.objects.filter(pk=package.pk).delete()

        with pytest.raises(SourcePackageError, match="has been reclaimed"):
            source_packages.generate_source_package_url(package)

        assert fake_bkrepo.signed == []

    def test_the_recorded_location_wins_over_the_current_setting(self, package, fake_bkrepo, settings):
        settings.BLOBSTORE_BUCKET_SOURCE_PACKAGES = "renamed-bucket"

        source_packages.generate_source_package_url(package)

        assert fake_bkrepo.signed[-1][0] == BUCKET

    def test_a_refused_signature_becomes_a_domain_error(self, package, fake_bkrepo):
        fake_bkrepo.fail_signing = True

        with pytest.raises(SourcePackageError, match="Signing a download URL"):
            source_packages.generate_source_package_url(package)

    # The wrapper runs the ORM on another thread, which only sees committed rows.
    @pytest.mark.django_db(transaction=True)
    async def test_the_async_wrapper_signs_the_same_way(self, package, fake_bkrepo):
        url = await source_packages.agenerate_source_package_url(package, expires_in=60)

        assert url
        assert fake_bkrepo.signed[-1][2] == 60
