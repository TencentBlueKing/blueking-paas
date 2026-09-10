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

"""Git persistence configuration and HTTP response schemas."""

from __future__ import annotations

from typing import Any, Self

import attrs
from ninja import Field, ModelSchema, Schema

from app_spark_api.infras.forgejo.entities import ForgejoClientConfig
from app_spark_api.repository.git.constants import DEFAULT_BACKEND_TYPE, DEFAULT_BRANCH
from app_spark_api.repository.git.exceptions import RepoServerConfigurationError
from app_spark_api.repository.git.models import ProjectGitRepository
from app_spark_api.utils import structure_config

_REQUIRED_STRING_FIELDS = (
    "base_url",
    "clone_url",
    "org",
    "service_account",
    "service_account_password",
    "default_branch",
    "commit_author_name",
    "commit_author_email",
)


@attrs.frozen
class RepoServerConfig:
    """How this service talks to the Git host (repo-server) that stores Project source.

    Git persistence is not a flag. Settings carry an unusable placeholder so tooling can
    boot without config; production must supply a real ``REPO_SERVER``, otherwise the
    first Git operation fails.

    Git identity is a robot, not the end user. Commits happen in the Agent, which
    is not the human sitting at the browser, and BlueKing users need not have an
    email Git would accept. ``commit_author_name`` / ``commit_author_email`` are
    therefore the App-Spark bot; later stages can put the user on a trailer.

    ``base_url`` is what *this* process uses (API calls). ``clone_url`` is what
    an Agent is told to clone from. They diverge as soon as one of them is not
    on localhost -- a sandbox that uses ``http://localhost:3000`` is talking to
    itself.

    :param type: Backend kind; only ``forgejo`` is implemented.
    :param base_url: Forgejo HTTP root as this service sees it.
    :param clone_url: Forgejo HTTP root as the Agent / git CLI should see it.
    :param org: Organisation every Project repository is created under.
    :param service_account: Username whose password is used to mint and revoke
        repository-scoped tokens (Basic Auth). Must not have 2FA.
    :param service_account_password: Password for that account; never logged.
    :param default_branch: Working branch created with the repository.
    :param timeout_seconds: HTTP timeout for Forgejo API calls.
    :param commit_author_name: ``user.name`` the Agent will commit as.
    :param commit_author_email: ``user.email`` the Agent will commit as.
    """

    type: str = DEFAULT_BACKEND_TYPE
    base_url: str = ""
    clone_url: str = ""
    org: str = ""
    service_account: str = ""
    service_account_password: str = attrs.field(default="", repr=False)
    default_branch: str = DEFAULT_BRANCH
    timeout_seconds: float = 30.0
    commit_author_name: str = "App-Spark"
    commit_author_email: str = "app-spark@localhost.invalid"

    def validate(self) -> None:
        """Reject a config that cannot actually talk to repo-server.

        :raises RepoServerConfigurationError: A required field is missing or the type is unknown.
        """
        if self.type != DEFAULT_BACKEND_TYPE:
            raise RepoServerConfigurationError(f"Unsupported repo-server type: {self.type}")
        for name in _REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise RepoServerConfigurationError(f"REPO_SERVER.{name} must not be empty")

    def forgejo_client_config(self) -> ForgejoClientConfig:
        """Connection settings for :class:`~app_spark_api.infras.forgejo.ForgejoClient`."""
        return ForgejoClientConfig(
            base_url=self.base_url,
            username=self.service_account,
            password=self.service_account_password,
            timeout_seconds=self.timeout_seconds,
        )

    def commit_identity(self) -> GitCommitIdentity:
        """Git author the Agent should commit as."""
        return GitCommitIdentity(author_name=self.commit_author_name, author_email=self.commit_author_email)


class GitCommitIdentity(Schema):
    """Robot identity used for Git commits, not the end user."""

    author_name: str = Field(description="提交所用的 user.name，机器账号而非终端用户")
    author_email: str = Field(description="提交所用的 user.email")


class GitRepositoryResponse(ModelSchema):
    """A Project's Git repository, without credential plaintext."""

    commit: GitCommitIdentity = Field(description="Agent 提交身份")

    class Meta:
        model = ProjectGitRepository
        fields = [
            "owner",
            "name",
            "default_branch",
            "status",
            "status_detail",
            "clone_url",
            "created",
            "updated",
        ]

    @classmethod
    def from_repository(cls, repo: ProjectGitRepository, *, commit: GitCommitIdentity) -> Self:
        """Assemble from the ORM row; attach commit identity from ``REPO_SERVER``.

        :param repo: Persisted ``ProjectGitRepository``.
        :param commit: Author identity from process config, not stored on the row.
        """
        model_names = {field.name for field in repo._meta.fields}
        data: dict[str, Any] = {name: getattr(repo, name) for name in cls.model_fields if name in model_names}
        data["commit"] = commit
        return cls.model_validate(data)


def structure_repo_server_config(raw_config: object) -> RepoServerConfig:
    """Structure ``REPO_SERVER`` from settings.

    Absent or empty is an error: a missing Git host cannot be structured.

    :param raw_config: Mapping from YAML / env, or ``None``.
    :return: A validated configuration.
    :raises RepoServerConfigurationError: Missing, empty, or unusable.
    """
    if raw_config in (None, "", {}):
        raise RepoServerConfigurationError(
            "REPO_SERVER is required: Git persistence talks to repo-server and has no off switch"
        )
    config = structure_config(raw_config, RepoServerConfig, error_cls=RepoServerConfigurationError)
    config.validate()
    return config
