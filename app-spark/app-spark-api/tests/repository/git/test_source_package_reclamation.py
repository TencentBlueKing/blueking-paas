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

"""Reclaiming source packages nobody has used for a while or whose Project is deleted, and the command."""

from __future__ import annotations

import io
from datetime import timedelta

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError, call_command
from django.utils import timezone

from app_spark_api.core.projects.models import Project
from app_spark_api.repository.git import source_packages
from app_spark_api.repository.git.models import ProjectSourcePackage
from app_spark_api.repository.storage.blob_stores import BkRepo

pytestmark = pytest.mark.django_db

BUCKET = "app-spark-source-packages"


@pytest.fixture
def make_package(project, fake_bkrepo):
    """Record a package last used ``days_ago`` days ago, with its blob in the fake BkRepo.

    The package belongs to the ``project`` fixture unless ``owner`` names another Project.
    """
    counter = iter(range(1, 1000))

    def make(days_ago: float, owner: Project | None = None) -> ProjectSourcePackage:
        owner = owner or project
        commit = format(next(counter), "040x")
        key = f"appspark-src-packages/{owner.pk}/{commit}/upload.tar.gz"
        fake_bkrepo.objects[(BUCKET, key)] = b"package"
        return ProjectSourcePackage.objects.create(
            project=owner,
            repo_full_name=f"app-spark/{owner.pk}",
            commit_sha=commit,
            bucket=BUCKET,
            key=key,
            size=len(b"package"),
            last_used_at=timezone.now() - timedelta(days=days_ago),
        )

    return make


class TestDeleteUnusedSourcePackages:
    def test_packages_unused_for_longer_lose_their_row_and_blob(self, make_package, fake_bkrepo):
        stale = make_package(days_ago=16)
        fresh = make_package(days_ago=14)

        reclaimed = source_packages.delete_unused_source_packages()

        assert [package.pk for package in reclaimed.packages] == [stale.pk]
        assert reclaimed.orphaned_keys == []
        assert list(ProjectSourcePackage.objects.values_list("pk", flat=True)) == [fresh.pk]
        assert set(fake_bkrepo.objects) == {(BUCKET, fresh.key)}

    def test_a_dry_run_deletes_nothing(self, make_package, fake_bkrepo):
        stale = make_package(days_ago=16)

        reclaimed = source_packages.delete_unused_source_packages(dry_run=True)

        assert [package.pk for package in reclaimed.packages] == [stale.pk]
        assert ProjectSourcePackage.objects.filter(pk=stale.pk).exists()
        assert (BUCKET, stale.key) in fake_bkrepo.objects

    @pytest.mark.parametrize("days", [1, 7])
    def test_a_window_shorter_than_a_url_lifetime_is_refused(self, make_package, days):
        """A package signed for the longest lifetime could otherwise vanish while its URL still works."""
        stale = make_package(days_ago=30)

        with pytest.raises(ValueError, match="must exceed the longest URL lifetime"):
            source_packages.delete_unused_source_packages(timedelta(days=days))

        assert ProjectSourcePackage.objects.filter(pk=stale.pk).exists()

    def test_a_package_reused_after_being_listed_is_kept(self, make_package, fake_bkrepo, monkeypatch):
        stale = make_package(days_ago=16)

        def store_while_a_release_reuses_it(bucket, key):
            # The moment between listing and locking the row: a release marks it used.
            ProjectSourcePackage.objects.filter(key=key).update(last_used_at=timezone.now())
            return BkRepo(bucket=bucket, key=key)

        monkeypatch.setattr(source_packages, "BkRepo", store_while_a_release_reuses_it)

        reclaimed = source_packages.delete_unused_source_packages()

        assert reclaimed.packages == []
        assert ProjectSourcePackage.objects.filter(pk=stale.pk).exists()
        assert (BUCKET, stale.key) in fake_bkrepo.objects

    def test_a_blob_that_cannot_be_deleted_is_reported_and_the_rest_carry_on(self, make_package, fake_bkrepo):
        first = make_package(days_ago=20)
        second = make_package(days_ago=16)
        fake_bkrepo.fail_deletes = True

        reclaimed = source_packages.delete_unused_source_packages()

        # Rows go first, so the failure orphans blobs rather than leaving rows without them.
        assert not ProjectSourcePackage.objects.exists()
        assert reclaimed.orphaned_keys == [first.key, second.key]

    def test_a_blob_bkrepo_refuses_to_delete_is_reported(self, make_package, fake_bkrepo):
        """BkRepo answers a refusal with an error code, not a network error, and it still orphans the blob."""
        stale = make_package(days_ago=16)
        fake_bkrepo.refuse_deletes_with = "250114"

        reclaimed = source_packages.delete_unused_source_packages()

        assert not ProjectSourcePackage.objects.filter(pk=stale.pk).exists()
        assert reclaimed.orphaned_keys == [stale.key]
        assert (BUCKET, stale.key) in fake_bkrepo.objects

    def test_a_blob_already_gone_is_not_reported(self, make_package, fake_bkrepo):
        stale = make_package(days_ago=16)
        del fake_bkrepo.objects[(BUCKET, stale.key)]

        reclaimed = source_packages.delete_unused_source_packages()

        assert [package.pk for package in reclaimed.packages] == [stale.pk]
        assert reclaimed.orphaned_keys == []

    def test_missing_bkrepo_configuration_deletes_no_row(self, make_package, settings):
        stale = make_package(days_ago=16)
        settings.BLOBSTORE_BKREPO_CONFIG = None

        with pytest.raises(ImproperlyConfigured):
            source_packages.delete_unused_source_packages()

        assert ProjectSourcePackage.objects.filter(pk=stale.pk).exists()


class TestDeleteProjectSourcePackages:
    @pytest.fixture
    def other_project(self, bk_user):
        return Project.objects.create(
            id="other-project",
            name="Other Project",
            creator=bk_user,
            owner=bk_user,
            tenant_id=bk_user.tenant_id,
        )

    def test_every_package_of_the_project_goes_however_recently_used(
        self, project, other_project, make_package, fake_bkrepo
    ):
        stale = make_package(days_ago=16)
        fresh = make_package(days_ago=0)
        unrelated = make_package(days_ago=16, owner=other_project)

        reclaimed = source_packages.delete_project_source_packages(project.pk)

        assert [package.pk for package in reclaimed.packages] == [stale.pk, fresh.pk]
        assert reclaimed.orphaned_keys == []
        assert list(ProjectSourcePackage.objects.values_list("pk", flat=True)) == [unrelated.pk]
        assert set(fake_bkrepo.objects) == {(BUCKET, unrelated.key)}

    def test_a_project_without_packages_needs_no_bkrepo_configuration(self, project, settings):
        settings.BLOBSTORE_BKREPO_CONFIG = None

        reclaimed = source_packages.delete_project_source_packages(project.pk)

        assert reclaimed == source_packages.Reclaimed(packages=[], orphaned_keys=[])

    def test_a_blob_that_cannot_be_deleted_is_reported_without_failing(self, project, make_package, fake_bkrepo):
        """Its row is already gone, so failing would not let a retry find the blob again."""
        package = make_package(days_ago=0)
        fake_bkrepo.fail_deletes = True

        reclaimed = source_packages.delete_project_source_packages(project.pk)

        assert not ProjectSourcePackage.objects.exists()
        assert reclaimed.orphaned_keys == [package.key]

    def test_missing_bkrepo_configuration_deletes_no_row(self, project, make_package, settings):
        package = make_package(days_ago=0)
        settings.BLOBSTORE_BKREPO_CONFIG = None

        with pytest.raises(ImproperlyConfigured):
            source_packages.delete_project_source_packages(project.pk)

        assert ProjectSourcePackage.objects.filter(pk=package.pk).exists()


class TestCommand:
    def test_by_default_packages_unused_for_15_days_are_deleted(self, make_package):
        stale = make_package(days_ago=15.1)
        fresh = make_package(days_ago=14.9)
        out = io.StringIO()

        call_command("delete_unused_source_packages", stdout=out)

        assert list(ProjectSourcePackage.objects.values_list("pk", flat=True)) == [fresh.pk]
        assert f"Deleted {stale.project_id}@{stale.commit_sha}" in out.getvalue()
        assert "Deleted 1 source package(s) unused for 15 day(s)." in out.getvalue()

    def test_the_window_and_dry_run_can_be_chosen(self, make_package):
        stale = make_package(days_ago=31)
        make_package(days_ago=29)
        out = io.StringIO()

        call_command("delete_unused_source_packages", "--days", "30", "--dry-run", stdout=out)

        assert ProjectSourcePackage.objects.count() == 2
        assert f"Would delete {stale.project_id}@{stale.commit_sha}" in out.getvalue()
        assert "Would delete 1 source package(s) unused for 30 day(s)." in out.getvalue()

    def test_a_too_short_window_fails_the_command(self, make_package):
        with pytest.raises(CommandError, match="must exceed the longest URL lifetime"):
            call_command("delete_unused_source_packages", "--days", "3")

    def test_orphaned_blobs_fail_the_command(self, make_package, fake_bkrepo):
        """So a scheduled run that leaves blobs behind is noticed rather than logged and forgotten."""
        stale = make_package(days_ago=16)
        fake_bkrepo.fail_deletes = True

        with pytest.raises(CommandError, match=f"Could not delete 1 blob\\(s\\) from BkRepo: {stale.key}"):
            call_command("delete_unused_source_packages", stdout=io.StringIO())

    def test_a_delete_bkrepo_refuses_fails_the_command(self, make_package, fake_bkrepo):
        stale = make_package(days_ago=16)
        fake_bkrepo.refuse_deletes_with = "251006"

        with pytest.raises(CommandError, match=f"Could not delete 1 blob\\(s\\) from BkRepo: {stale.key}"):
            call_command("delete_unused_source_packages", stdout=io.StringIO())
