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

"""Where a download is offered, and connection ownership once one starts.

The endpoint tests cover what a caller sees. What they cannot see is whether the upstream
connection is handed back, and a download that leaks one per abandoned request would fail
slowly and only in production.
"""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import resolve

from app_spark_api.infras.forgejo.exceptions import ForgejoUnavailableError
from app_spark_api.repository.git import archives
from app_spark_api.repository.git.services import provision_project_repository
from app_spark_api.utils.urls import to_path_info

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def clients(fake_forgejo, monkeypatch):
    """Hand back every async client the code under test builds, so it can be inspected."""
    built = []

    def factory(*args, **kwargs):
        client = fake_forgejo.async_client()
        built.append(client)
        return client

    monkeypatch.setattr("app_spark_api.repository.git.archives.make_forgejo_async_client", factory)
    return built


@pytest.fixture
def repo(project, fake_forgejo):
    return provision_project_repository(project)


def test_a_provisioned_repository_is_offered_at_the_archive_route(repo):
    url = archives.archive_url_for(repo)

    assert url is not None
    # Resolving it back is the point: renaming the route in `api.py` would otherwise
    # only surface as a reverse failure while serving a real request.
    match = resolve(to_path_info(url))
    assert match.url_name == "git-repository-archive"
    assert match.kwargs["project_id"] == repo.project_id


def test_a_repository_without_a_remote_is_offered_nothing(repo):
    """Provisioning has not reached Forgejo yet, so there is nothing to archive."""
    repo.remote_id = None

    assert archives.archive_url_for(repo) is None


async def test_draining_the_archive_releases_the_client(repo, clients):
    archive = await archives.open_project_source_archive(repo)

    body = b"".join([chunk async for chunk in archive.chunks])

    assert body
    assert len(clients) == 1
    assert clients[0]._client.is_closed, "reading to the end must hand the connection back"


async def test_abandoning_the_archive_part_way_releases_the_client(repo, clients):
    """Django stops iterating when the browser disconnects; that must not leak a client."""
    archive = await archives.open_project_source_archive(repo)
    chunks = archive.chunks
    await anext(chunks)
    assert not clients[0]._client.is_closed

    # What Django does to a streaming response whose client went away.
    await chunks.aclose()

    assert clients[0]._client.is_closed


async def test_a_failure_before_the_body_releases_the_client(repo, clients, fake_forgejo):
    """Nothing else will close it: on this path no ``chunks`` generator is ever handed out."""
    fake_forgejo.archive_status = HTTPStatus.INTERNAL_SERVER_ERROR

    with pytest.raises(ForgejoUnavailableError):
        await archives.open_project_source_archive(repo)

    assert len(clients) == 1
    assert clients[0]._client.is_closed


async def test_the_commit_comes_from_the_working_branch_tip(repo, clients, fake_forgejo):
    fake_forgejo.heads[(repo.owner, repo.name)] = "cafe" + "0" * 36

    archive = await archives.open_project_source_archive(repo)

    try:
        assert archive.commit == "cafe" + "0" * 36
        assert archive.filename == f"{repo.project_id}-cafe000.zip"
        assert archive.media_type == "application/zip"
    finally:
        await archive.chunks.aclose()
