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

from app_spark_api.repository.git.entities import (
    GitCommitIdentity,
    GitRepositoryResponse,
    structure_repo_server_config,
)
from app_spark_api.repository.git.exceptions import RepoServerConfigurationError
from tests.infras.forgejo.fake import SERVICE_PASSWORD, repo_server_config


def test_missing_or_empty_config_is_an_error():
    with pytest.raises(RepoServerConfigurationError, match="required"):
        structure_repo_server_config(None)
    with pytest.raises(RepoServerConfigurationError, match="required"):
        structure_repo_server_config({})
    with pytest.raises(RepoServerConfigurationError, match="required"):
        structure_repo_server_config("")


def test_config_requires_the_forgejo_fields():
    with pytest.raises(RepoServerConfigurationError, match="base_url"):
        structure_repo_server_config({"type": "forgejo"})


def test_an_unknown_backend_type_is_refused():
    payload = repo_server_config(type="github")
    with pytest.raises(RepoServerConfigurationError, match="github"):
        structure_repo_server_config(payload)


def test_service_account_password_is_not_in_repr():
    config = structure_repo_server_config(repo_server_config())
    assert SERVICE_PASSWORD not in repr(config)


@pytest.mark.django_db(transaction=True)
def test_git_repository_response_copies_model_fields_and_nests_commit(project, fake_forgejo):
    from app_spark_api.repository.git.services import provision_project_repository

    repo = provision_project_repository(project)
    body = GitRepositoryResponse.from_repository(
        repo,
        commit=GitCommitIdentity(author_name="Bot", author_email="bot@example.invalid"),
    )
    dumped = body.model_dump()
    assert dumped["owner"] == repo.owner
    assert dumped["name"] == repo.name
    assert dumped["status"] == repo.status
    assert dumped["commit"] == {"author_name": "Bot", "author_email": "bot@example.invalid"}
    assert "write_token" not in dumped
    assert "write_token_id" not in dumped
