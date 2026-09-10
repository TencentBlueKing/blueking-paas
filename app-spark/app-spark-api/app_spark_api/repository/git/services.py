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

"""Provisioning a Project's private Git repository and its long-lived write token.

Remote work happens outside the Project-insert transaction: a Forgejo blip must
not roll back a Project that already exists. Failures are recorded on the
``ProjectGitRepository`` row so an explicit retry can pick them up.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
from django.db import transaction

from app_spark_api.infras.forgejo.exceptions import ForgejoError
from app_spark_api.repository.git.constants import (
    READ_TOKEN_SCOPE,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_READY,
    WRITE_TOKEN_SCOPE,
    read_token_name,
    write_token_name,
)
from app_spark_api.repository.git.exceptions import GitBackendError, GitRepositoryNotReadyError
from app_spark_api.repository.git.factory import get_repo_server_config, make_forgejo_client
from app_spark_api.repository.git.models import ProjectGitRepository

if TYPE_CHECKING:
    from app_spark_api.core.projects.models import Project
    from app_spark_api.infras.forgejo.client import ForgejoClient
    from app_spark_api.repository.git.entities import RepoServerConfig

logger = logging.getLogger(__name__)

_REMOTE_ERRORS = (GitBackendError, ForgejoError)


def clone_url_for(config: RepoServerConfig, owner: str, name: str) -> str:
    """HTTP clone URL as the Agent should see it, not as Forgejo advertises it."""
    return f"{config.clone_url.rstrip('/')}/{owner}/{name}.git"


def provision_project_repository(
    project: Project,
    *,
    client: ForgejoClient | None = None,
) -> ProjectGitRepository:
    """Create or repair the Project's private repository and write token.

    Holds a row lock for the remote calls so two concurrent provisions cannot
    each mint a token and then revoke the other's. Project creation is rare
    enough that a few seconds of lock is the simpler correctness.

    :param project: Already-persisted Project.
    :param client: Injected Forgejo client; production builds one from settings.
    :return: The repository row, ``ready`` or ``failed``.
    """
    config = get_repo_server_config()

    with transaction.atomic():
        repo, _created = ProjectGitRepository.objects.select_for_update().get_or_create(
            project=project,
            defaults={
                "owner": config.org,
                "name": project.id,
                "default_branch": config.default_branch,
                "status": STATUS_PENDING,
                "clone_url": clone_url_for(config, config.org, project.id),
            },
        )
        if repo.status == STATUS_READY and repo.write_token and repo.write_token_id:
            return repo
        owned_client = client is None
        forgejo = client or make_forgejo_client(config)
        try:
            _provision_remote(repo, config, forgejo)
        except _REMOTE_ERRORS as exc:
            repo.status = STATUS_FAILED
            repo.status_detail = str(exc)
            repo.save()
            logger.exception("Provisioning Git repository for project %s failed", project.id)
            return repo
        finally:
            if owned_client:
                forgejo.close()
        return repo


def revoke_project_credentials(
    project: Project,
    *,
    client: ForgejoClient | None = None,
) -> ProjectGitRepository:
    """Revoke the stored write token. Lifecycle / emergency only, not per-turn.

    After this the row is ``failed`` until provision is called again (which
    re-issues a token against the existing repository).
    """
    config = get_repo_server_config()

    with transaction.atomic():
        try:
            repo = ProjectGitRepository.objects.select_for_update().get(project=project)
        except ProjectGitRepository.DoesNotExist as exc:
            raise GitRepositoryNotReadyError(f"Project {project.id} has no Git repository") from exc
        owned_client = client is None
        forgejo = client or make_forgejo_client(config)
        try:
            if repo.write_token_id is not None:
                forgejo.delete_token(repo.write_token_id)
            forgejo.delete_tokens_named(write_token_name(project.id))
        except _REMOTE_ERRORS as exc:
            repo.status = STATUS_FAILED
            repo.status_detail = f"revoke failed: {exc}"
            repo.save()
            raise
        finally:
            if owned_client:
                forgejo.close()
        repo.write_token = None
        repo.write_token_id = None
        repo.status = STATUS_FAILED
        repo.status_detail = "credentials revoked"
        repo.save()
        return repo


def require_project_git_ready(project_id: str) -> ProjectGitRepository:
    """Refuse to start an Agent unless the Project's repository is ``ready``.

    :raises GitRepositoryNotReadyError: The repo is missing or not ready.
    """
    try:
        repo = ProjectGitRepository.objects.get(project_id=project_id)
    except ProjectGitRepository.DoesNotExist as exc:
        raise GitRepositoryNotReadyError(
            f"Project {project_id} has no Git repository; call the provision endpoint"
        ) from exc
    if repo.status != STATUS_READY or not repo.write_token:
        raise GitRepositoryNotReadyError(
            f"Project {project_id} Git repository is {repo.status}"
            + (f": {repo.status_detail}" if repo.status_detail else "")
        )
    return repo


async def arequire_project_git_ready(project_id: str) -> None:
    """Async wrapper for :func:`require_project_git_ready`."""
    await sync_to_async(require_project_git_ready)(project_id)


async def aprovision_project_repository(project: Project) -> ProjectGitRepository:
    return await sync_to_async(provision_project_repository)(project)


async def arevoke_project_credentials(project: Project) -> ProjectGitRepository:
    return await sync_to_async(revoke_project_credentials)(project)


def _provision_remote(repo: ProjectGitRepository, config: RepoServerConfig, client: ForgejoClient) -> None:
    remote = client.ensure_private_repo(
        owner=config.org,
        name=repo.name,
        default_branch=config.default_branch,
    )
    client.ensure_branch_protection(remote.owner, remote.name, config.default_branch)
    write = client.reissue_repo_token(
        name=write_token_name(repo.project_id),
        scopes=[WRITE_TOKEN_SCOPE],
        owner=remote.owner,
        repo_name=remote.name,
    )
    read = client.reissue_repo_token(
        name=read_token_name(repo.project_id),
        scopes=[READ_TOKEN_SCOPE],
        owner=remote.owner,
        repo_name=remote.name,
    )
    try:
        client.verify_read_token_cannot_write(read, remote.owner, remote.name)
    finally:
        client.delete_token(read.token_id)
    repo.remote_id = remote.remote_id
    repo.owner = remote.owner
    repo.name = remote.name
    repo.default_branch = remote.default_branch or config.default_branch
    repo.clone_url = clone_url_for(config, remote.owner, remote.name)
    repo.write_token = write.sha1
    repo.write_token_id = write.token_id
    repo.status = STATUS_READY
    repo.status_detail = ""
    repo.save()
