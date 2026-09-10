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

"""End-to-end Git isolation against a real Forgejo.

Never skipped. Run with ``APP_SPARK_FORGEJO_LIVE=1``; the session fixture starts
``repo-server/forgejo`` (``just test-up``) the same way conversation tests spawn
the Agent. Missing Forgejo or credentials fail the job.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import tempfile
from http import HTTPStatus
from pathlib import Path

import pytest
from asgiref.sync import sync_to_async
from django.db import connection

from app_spark_api.infras.forgejo import ForgejoClient
from app_spark_api.repository.git.constants import READ_TOKEN_SCOPE, STATUS_READY, read_token_name
from app_spark_api.repository.git.entities import RepoServerConfig
from app_spark_api.repository.git.models import ProjectGitRepository

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.forgejo]

GIT = shutil.which("git") or "git"


@pytest.fixture
def forgejo_settings(settings, forgejo_live_env):
    if shutil.which("git") is None:
        pytest.fail("git is required on PATH for live Forgejo tests")
    base_url = forgejo_live_env["base_url"]
    password = forgejo_live_env["password"]
    org = forgejo_live_env["org"]
    account = forgejo_live_env["account"]
    settings.REPO_SERVER = {
        "type": "forgejo",
        "base_url": base_url,
        "clone_url": base_url,
        "org": org,
        "service_account": account,
        "service_account_password": password,
        "default_branch": "main",
        "commit_author_name": "App-Spark",
        "commit_author_email": "app-spark@localhost.invalid",
    }
    return RepoServerConfig(
        type="forgejo",
        base_url=base_url,
        clone_url=base_url,
        org=org,
        service_account=account,
        service_account_password=password,
    )


def _project_id(prefix: str) -> str:
    # Project IDs are 2-20 chars, lowercase starting with a letter.
    return f"{prefix}{secrets.token_hex(4)}"[:20]


def _git(token: str, *args: str, cwd: Path, username: str) -> subprocess.CompletedProcess[str]:
    import base64

    header = "Authorization: Basic " + base64.b64encode(f"{username}:{token}".encode()).decode()
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "true"
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "commit.gpgsign"
    env["GIT_CONFIG_VALUE_0"] = "false"
    return subprocess.run(
        [GIT, "-c", f"http.extraHeader={header}", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


async def _create_project(client, project_id: str) -> dict:
    response = await client.post(
        "/api/projects/",
        data={"id": project_id, "name": project_id},
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.CREATED, response.content
    return (await client.get(f"/api/projects/{project_id}/git-repository/")).json()


def _clone_and_push(clone_url: str, token: str, username: str, filename: str) -> subprocess.CompletedProcess[str]:
    work = Path(tempfile.mkdtemp(prefix="forgejo-live-"))
    cloned = _git(token, "clone", clone_url, str(work / "repo"), cwd=work, username=username)
    if cloned.returncode != 0:
        return cloned
    repo = work / "repo"
    (repo / filename).write_text(f"live {secrets.token_hex(4)}\n")
    for cmd in (
        ["config", "user.name", "App-Spark"],
        ["config", "user.email", "app-spark@localhost.invalid"],
        ["add", filename],
        ["commit", "-m", "live"],
        ["push", "origin", "HEAD"],
    ):
        result = _git(token, *cmd, cwd=repo, username=username)
        if result.returncode != 0:
            return result
    return result


def _ciphertext_for(project_id: str) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT write_token FROM git_projectgitrepository WHERE project_id = %s", [project_id])
        return cursor.fetchone()[0]


async def test_two_projects_get_isolated_private_repositories(aapi_client, forgejo_settings):
    id_a = _project_id("la")
    id_b = _project_id("lb")
    git_a = await _create_project(aapi_client, id_a)
    git_b = await _create_project(aapi_client, id_b)
    assert git_a["status"] == STATUS_READY
    assert git_b["status"] == STATUS_READY

    row_a = await ProjectGitRepository.objects.aget(project_id=id_a)
    row_b = await ProjectGitRepository.objects.aget(project_id=id_b)
    assert row_a.write_token
    assert row_b.write_token
    assert row_a.write_token != row_b.write_token

    raw = await sync_to_async(_ciphertext_for)(id_a)
    assert raw.startswith("bkcrypt$")
    assert row_a.write_token not in raw

    username = forgejo_settings.service_account
    pushed_a = _clone_and_push(row_a.clone_url, row_a.write_token, username, "a.txt")
    assert pushed_a.returncode == 0, pushed_a.stderr

    work = Path(tempfile.mkdtemp(prefix="forgejo-cross-"))
    cross = _git(row_a.write_token, "clone", row_b.clone_url, str(work / "b"), cwd=work, username=username)
    assert cross.returncode != 0, "A's token must not clone B"

    pushed_b_with_a = _clone_and_push(row_b.clone_url, row_a.write_token, username, "x.txt")
    assert pushed_b_with_a.returncode != 0

    pushed_b = _clone_and_push(row_b.clone_url, row_b.write_token, username, "b.txt")
    assert pushed_b.returncode == 0, pushed_b.stderr

    # Read token: clone yes, push no.
    with ForgejoClient(forgejo_settings.forgejo_client_config()) as client:
        read = client.reissue_repo_token(
            name=read_token_name(id_a) + "-live",
            scopes=[READ_TOKEN_SCOPE],
            owner=forgejo_settings.org,
            repo_name=id_a,
        )
        assert read.sha1
        cloned = _git(read.sha1, "clone", row_a.clone_url, str(work / "read"), cwd=work, username=username)
        assert cloned.returncode == 0, cloned.stderr
        pushed_read = _clone_and_push(row_a.clone_url, read.sha1, username, "from-read.txt")
        assert pushed_read.returncode != 0
        client.delete_token(read.token_id)

    anonymous = subprocess.run(  # noqa: ASYNC221
        [GIT, "ls-remote", row_a.clone_url],
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert anonymous.returncode != 0

    revoked = await aapi_client.post(f"/api/projects/{id_a}/git-repository/revoke-credentials/")
    assert revoked.status_code == HTTPStatus.OK
    after = _git(row_a.write_token, "ls-remote", row_a.clone_url, cwd=work, username=username)
    assert after.returncode != 0
