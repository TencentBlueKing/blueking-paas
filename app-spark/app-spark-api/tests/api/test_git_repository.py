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

from http import HTTPStatus

import pytest

from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.repository.git.constants import STATUS_READY
from app_spark_api.repository.git.models import ProjectGitRepository

pytestmark = pytest.mark.django_db(transaction=True)

PROJECT_ID = "spark-demo"


def git_url(project_id: str = PROJECT_ID) -> str:
    return f"/api/projects/{project_id}/git-repository/"


async def test_creating_a_project_provisions_its_repository(aapi_client, fake_forgejo):
    response = await aapi_client.post(
        "/api/projects/",
        data={"id": PROJECT_ID, "name": "Spark Demo"},
        content_type="application/json",
    )

    assert response.status_code == HTTPStatus.CREATED
    repo = await ProjectGitRepository.objects.aget(project_id=PROJECT_ID)
    assert repo.status == STATUS_READY
    assert ("app-spark", PROJECT_ID) in fake_forgejo.repos
    body = (await aapi_client.get(git_url())).json()
    assert body["status"] == STATUS_READY
    assert body["name"] == PROJECT_ID
    assert "write_token" not in body
    assert body["commit"] == {"author_name": "App-Spark", "author_email": "app-spark@localhost.invalid"}


async def test_a_failed_provision_leaves_the_project_and_can_be_retried(aapi_client, fake_forgejo):
    fake_forgejo.fail_next_request = True
    created = await aapi_client.post(
        "/api/projects/",
        data={"id": PROJECT_ID, "name": "Spark Demo"},
        content_type="application/json",
    )
    assert created.status_code == HTTPStatus.CREATED
    assert (await ProjectGitRepository.objects.aget(project_id=PROJECT_ID)).status == "failed"

    retried = await aapi_client.post(git_url() + "provision/")
    assert retried.status_code == HTTPStatus.OK
    assert retried.json()["status"] == STATUS_READY


async def test_revoke_is_an_explicit_endpoint(aapi_client, fake_forgejo):
    await aapi_client.post(
        "/api/projects/",
        data={"id": PROJECT_ID, "name": "Spark Demo"},
        content_type="application/json",
    )

    revoked = await aapi_client.post(git_url() + "revoke-credentials/")

    assert revoked.status_code == HTTPStatus.OK
    assert revoked.json()["status"] == "failed"
    repo = await ProjectGitRepository.objects.aget(project_id=PROJECT_ID)
    assert repo.write_token is None


async def test_starting_an_agent_requires_a_ready_repository(aapi_client, fake_forgejo, settings, tmp_path):
    settings.AGENT_RUNTIME_PROVIDER = "local_process"
    settings.AGENT_RUNTIME_PROVIDER_CONFIG = {
        "agent_project_dir": str(tmp_path / "agent"),
        "workspace_root": str(tmp_path / "workspaces"),
        "state_root": str(tmp_path / "agent-state"),
    }
    await aapi_client.post(
        "/api/projects/",
        data={"id": PROJECT_ID, "name": "Spark Demo"},
        content_type="application/json",
    )
    await aapi_client.post(git_url() + "revoke-credentials/")

    response = await aapi_client.post(f"/api/projects/{PROJECT_ID}/conversations/")

    assert response.status_code == HTTPStatus.CONFLICT
    assert "Git repository" in response.json()["detail"]


async def test_git_endpoints_are_auth_protected(aanonymous_api_client, bk_user):
    response = await aanonymous_api_client.get(git_url())
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_is_not_found_when_the_project_has_no_repository(aapi_client, bk_user):
    from app_spark_api.core.projects.models import Project

    await Project.objects.acreate(
        id=PROJECT_ID,
        name="Spark Demo",
        creator=bk_user,
        owner=bk_user,
        tenant_id=get_tenant(bk_user).id,
    )

    response = await aapi_client.get(git_url())
    assert response.status_code == HTTPStatus.NOT_FOUND
