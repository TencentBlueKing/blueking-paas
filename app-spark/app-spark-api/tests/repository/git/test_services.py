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

from __future__ import annotations

import threading

import pytest
from django.db import connection, connections

from app_spark_api.repository.git.constants import STATUS_FAILED, STATUS_READY, write_token_name
from app_spark_api.repository.git.exceptions import GitRepositoryNotReadyError
from app_spark_api.repository.git.models import ProjectGitRepository
from app_spark_api.repository.git.services import (
    provision_project_repository,
    require_project_git_ready,
    revoke_project_credentials,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_provision_creates_a_private_repo_and_encrypts_the_write_token(project, fake_forgejo):
    repo = provision_project_repository(project)

    assert repo.status == STATUS_READY
    assert repo.write_token
    assert repo.write_token_id
    assert repo.clone_url == "http://git-for-agent.invalid/app-spark/test-project.git"
    assert (repo.owner, repo.name, "main") in fake_forgejo.protections

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT write_token FROM git_projectgitrepository WHERE project_id = %s",
            [project.id],
        )
        raw = cursor.fetchone()[0]
    assert raw.startswith("bkcrypt$")
    assert repo.write_token not in raw


def test_a_second_provision_reuses_the_ready_row(project, fake_forgejo):
    first = provision_project_repository(project)
    token_ids = set(fake_forgejo.tokens)
    second = provision_project_repository(project)

    assert second.pk == first.pk
    assert second.write_token == first.write_token
    assert set(fake_forgejo.tokens) == token_ids


def test_a_lost_create_response_is_reattached(project, fake_forgejo):
    fake_forgejo.drop_next_create_response = True

    repo = provision_project_repository(project)

    assert repo.status == STATUS_READY
    assert repo.remote_id == fake_forgejo.repos[("app-spark", "test-project")]["id"]


def test_a_lost_token_response_is_revoked_and_reissued(project, fake_forgejo):
    fake_forgejo.drop_next_token_response = True
    failed = provision_project_repository(project)
    leftovers = [t for t in fake_forgejo.tokens.values() if t["name"] == write_token_name(project.id)]

    assert failed.status == STATUS_FAILED
    assert len(leftovers) == 1

    repo = provision_project_repository(project)
    named = [t for t in fake_forgejo.tokens.values() if t["name"] == write_token_name(project.id)]

    assert repo.status == STATUS_READY
    assert len(named) == 1
    assert named[0]["sha1"] == repo.write_token
    assert named[0]["id"] != leftovers[0]["id"]


def test_a_remote_failure_keeps_the_project_and_records_failed(project, fake_forgejo):
    fake_forgejo.fail_next_request = True

    repo = provision_project_repository(project)

    assert repo.status == STATUS_FAILED
    assert project.id == "test-project"
    assert ProjectGitRepository.objects.get(project=project).status == STATUS_FAILED


def test_retry_after_failure_reaches_ready(project, fake_forgejo):
    fake_forgejo.fail_next_request = True
    provision_project_repository(project)

    repo = provision_project_repository(project)

    assert repo.status == STATUS_READY


def test_revoke_drops_the_remote_token_and_blocks_ready(project, fake_forgejo):
    provision_project_repository(project)

    revoked = revoke_project_credentials(project)

    assert revoked.status == STATUS_FAILED
    assert revoked.write_token is None
    assert not any(t["name"] == write_token_name(project.id) for t in fake_forgejo.tokens.values())
    with pytest.raises(GitRepositoryNotReadyError):
        require_project_git_ready(project.id)


def test_require_ready_refuses_a_missing_or_failed_row(project, fake_forgejo):
    with pytest.raises(GitRepositoryNotReadyError):
        require_project_git_ready(project.id)

    fake_forgejo.fail_next_request = True
    provision_project_repository(project)
    with pytest.raises(GitRepositoryNotReadyError):
        require_project_git_ready(project.id)


def test_concurrent_provision_converges_on_one_write_token(project, fake_forgejo):
    results: list = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            results.append(provision_project_repository(project))
        except BaseException as exc:  # noqa: BLE001 - collect any thread failure
            errors.append(exc)
        finally:
            connections.close_all()

    workers = [threading.Thread(target=run) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert not errors
    assert {row.status for row in results} == {STATUS_READY}
    writes = [token for token in fake_forgejo.tokens.values() if token["name"] == write_token_name(project.id)]
    assert len(writes) == 1
