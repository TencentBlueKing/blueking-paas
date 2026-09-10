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

import pytest

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
