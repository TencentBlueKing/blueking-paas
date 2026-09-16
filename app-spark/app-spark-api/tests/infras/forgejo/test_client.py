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

import json
from http import HTTPStatus

import httpx2
import pytest

from app_spark_api.infras.forgejo.client import ForgejoClient
from app_spark_api.infras.forgejo.entities import AccessToken
from app_spark_api.infras.forgejo.exceptions import ForgejoUnavailableError
from app_spark_api.repository.git.constants import READ_TOKEN_SCOPE, WRITE_TOKEN_SCOPE
from tests.infras.forgejo.fake import ORG, SERVICE_ACCOUNT, SERVICE_PASSWORD, FakeForgejo, forgejo_client_config


def _client(fake: FakeForgejo):
    return fake.client(forgejo_client_config())


def test_ensure_private_repo_creates_once_and_reattaches():
    fake = FakeForgejo()
    client = _client(fake)

    first = client.ensure_private_repo(owner=ORG, name="spark-a", default_branch="main")
    second = client.ensure_private_repo(owner=ORG, name="spark-a", default_branch="main")

    assert first.remote_id == second.remote_id
    assert first.private is True
    assert len(fake.repos) == 1


def test_a_lost_create_response_is_recovered_by_get():
    fake = FakeForgejo()
    fake.drop_next_create_response = True
    client = _client(fake)

    repo = client.ensure_private_repo(owner=ORG, name="spark-a", default_branch="main")

    assert repo.name == "spark-a"
    assert (ORG, "spark-a") in fake.repos


def test_a_public_repository_is_refused():
    fake = FakeForgejo()
    fake.repos[(ORG, "public-one")] = {
        "id": 9,
        "name": "public-one",
        "owner": {"login": ORG},
        "private": False,
        "default_branch": "main",
    }
    client = _client(fake)

    with pytest.raises(ForgejoUnavailableError, match="public"):
        client.ensure_private_repo(owner=ORG, name="public-one", default_branch="main")


def test_reissue_revokes_a_leftover_token_then_returns_a_new_secret():
    fake = FakeForgejo()
    client = _client(fake)
    client.ensure_private_repo(owner=ORG, name="spark-a", default_branch="main")
    # Forgejo created the token but the body never arrived; the leftover stays.
    fake.drop_next_token_response = True
    with pytest.raises(ForgejoUnavailableError):
        client.create_token(
            name="app-spark-spark-a-write",
            scopes=[WRITE_TOKEN_SCOPE],
            owner=ORG,
            repo_name="spark-a",
        )
    leftover_ids = set(fake.tokens)
    assert leftover_ids

    reissued = client.reissue_repo_token(
        name="app-spark-spark-a-write",
        scopes=[WRITE_TOKEN_SCOPE],
        owner=ORG,
        repo_name="spark-a",
    )

    assert leftover_ids.isdisjoint(fake.tokens)
    assert reissued.sha1
    assert reissued.token_id not in leftover_ids


def test_a_read_token_can_see_the_repo_but_cannot_write():
    fake = FakeForgejo()
    client = _client(fake)
    client.ensure_private_repo(owner=ORG, name="spark-a", default_branch="main")
    read = client.create_token(
        name="app-spark-spark-a-read",
        scopes=[READ_TOKEN_SCOPE],
        owner=ORG,
        repo_name="spark-a",
    )

    client.verify_read_token_cannot_write(read, ORG, "spark-a")


def test_a_read_token_for_one_repo_cannot_see_another():
    fake = FakeForgejo()
    client = _client(fake)
    client.ensure_private_repo(owner=ORG, name="spark-a", default_branch="main")
    client.ensure_private_repo(owner=ORG, name="spark-b", default_branch="main")
    token = client.create_token(
        name="only-a",
        scopes=[WRITE_TOKEN_SCOPE],
        owner=ORG,
        repo_name="spark-a",
    )

    with pytest.raises(ForgejoUnavailableError, match="read token could not GET"):
        client.verify_read_token_cannot_write(token, ORG, "spark-b")


def test_branch_protection_is_idempotent():
    fake = FakeForgejo()
    client = _client(fake)
    client.ensure_private_repo(owner=ORG, name="spark-a", default_branch="main")

    client.ensure_branch_protection(ORG, "spark-a", "main")
    client.ensure_branch_protection(ORG, "spark-a", "main")

    assert (ORG, "spark-a", "main") in fake.protections


def test_connect_errors_become_client_errors():
    fake = FakeForgejo()
    fake.fail_next_request = True
    client = _client(fake)

    with pytest.raises(ForgejoUnavailableError, match="failed"):
        client.get_repo(ORG, "missing")


def test_service_account_credentials_are_not_in_repr():
    config = forgejo_client_config()
    assert SERVICE_ACCOUNT in repr(config)
    assert SERVICE_PASSWORD not in repr(config)


@pytest.mark.parametrize("create_status", [403, 404, 409, 422])
def test_only_create_conflicts_fall_back_to_patching_branch_protection(create_status):
    methods = []

    def respond(request):
        methods.append(request.method)
        if request.method == "GET":
            return httpx2.Response(404)
        if request.method == "POST":
            return httpx2.Response(create_status, text="original create error")
        return httpx2.Response(200)

    with ForgejoClient(forgejo_client_config(), transport=httpx2.MockTransport(respond)) as client:
        if create_status in {409, 422}:
            client.ensure_branch_protection(ORG, "spark-a", "main")
            assert methods == ["GET", "POST", "PATCH"]
        else:
            with pytest.raises(ForgejoUnavailableError, match=f"POST branch protection.*HTTP {create_status}"):
                client.ensure_branch_protection(ORG, "spark-a", "main")
            assert methods == ["GET", "POST"]


def test_an_existing_branch_rule_is_patched_without_trying_to_create_it():
    methods = []

    def respond(request):
        methods.append(request.method)
        return httpx2.Response(403 if request.method == "POST" else 200)

    with ForgejoClient(forgejo_client_config(), transport=httpx2.MockTransport(respond)) as client:
        client.ensure_branch_protection(ORG, "spark-a", "main")
    assert methods == ["GET", "PATCH"]


def test_branch_rule_query_permission_error_does_not_attempt_a_write():
    def respond(request):
        assert request.method == "GET"
        return httpx2.Response(403)

    with (
        ForgejoClient(forgejo_client_config(), transport=httpx2.MockTransport(respond)) as client,
        pytest.raises(ForgejoUnavailableError, match=r"GET branch protection.*403"),
    ):
        client.ensure_branch_protection(ORG, "spark-a", "main")


@pytest.mark.parametrize("status", [204, 404, 403, 500])
def test_delete_by_name_never_lists_account_tokens(status):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx2.Response(status)

    with ForgejoClient(forgejo_client_config(), transport=httpx2.MockTransport(respond)) as client:
        if status in {204, 404}:
            client.delete_tokens_named("app-spark-spark-a-write")
        else:
            with pytest.raises(ForgejoUnavailableError, match=f"HTTP {status}"):
                client.delete_tokens_named("app-spark-spark-a-write")
    assert [(r.method, r.url.path) for r in requests] == [
        ("DELETE", f"/api/v1/users/{SERVICE_ACCOUNT}/tokens/app-spark-spark-a-write")
    ]


@pytest.mark.parametrize("read_status", [403, 404])
def test_read_permission_requires_a_successful_repo_query(read_status):
    def respond(request):
        assert request.method == "GET"
        return httpx2.Response(read_status)

    with (
        ForgejoClient(forgejo_client_config(), transport=httpx2.MockTransport(respond)) as client,
        pytest.raises(ForgejoUnavailableError, match=f"read token could not GET.*{read_status}"),
    ):
        client.verify_read_token_cannot_write(AccessToken(token_id=1, name="read", sha1="read-secret"), ORG, "a")


@pytest.mark.parametrize("write_status", [401, 404, 409, 422, 500, 503])
def test_inconclusive_write_probe_does_not_pass_verification(write_status):
    def respond(request):
        return httpx2.Response(200 if request.method == "GET" else write_status)

    with (
        ForgejoClient(forgejo_client_config(), transport=httpx2.MockTransport(respond)) as client,
        pytest.raises(ForgejoUnavailableError, match=f"inconclusive.*{write_status}"),
    ):
        client.verify_read_token_cannot_write(AccessToken(token_id=1, name="read", sha1="read-secret"), ORG, "a")


@pytest.mark.parametrize("cleanup_status", [200, 500])
def test_a_successful_write_probe_is_cleaned_up_and_still_fails_verification(cleanup_status, caplog):
    requests = []

    def respond(request):
        requests.append(request)
        if request.method == "POST":
            return httpx2.Response(HTTPStatus.CREATED, json={"content": {"sha": "probe-blob-sha"}})
        return httpx2.Response(cleanup_status if request.method == "DELETE" else 200)

    with (
        ForgejoClient(forgejo_client_config(), transport=httpx2.MockTransport(respond)) as client,
        pytest.raises(ForgejoUnavailableError, match="read token was allowed to write"),
    ):
        client.verify_read_token_cannot_write(AccessToken(token_id=1, name="read", sha1="read-secret"), ORG, "a")

    assert [r.method for r in requests] == ["GET", "POST", "DELETE"]
    assert requests[1].url.path == requests[2].url.path
    assert "/contents/.app-spark-read-token-probe-" in requests[2].url.path
    assert requests[1].headers["authorization"] == "token read-secret"
    assert requests[2].headers["authorization"].startswith("Basic ")
    assert json.loads(requests[2].content)["sha"] == "probe-blob-sha"
    assert ("Could not clean up read-token probe" in caplog.text) == (cleanup_status == 500)


def test_read_probe_connection_errors_become_client_errors():
    def respond(request):
        raise httpx2.ConnectError("connection refused")

    with (
        ForgejoClient(forgejo_client_config(), transport=httpx2.MockTransport(respond)) as client,
        pytest.raises(ForgejoUnavailableError, match="Read-token verification failed"),
    ):
        client.verify_read_token_cannot_write(AccessToken(token_id=1, name="read", sha1="read-secret"), ORG, "a")
