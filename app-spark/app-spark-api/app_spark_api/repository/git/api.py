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
from typing import TYPE_CHECKING

from django.shortcuts import aget_object_or_404
from ninja import Path, Router, Status

from app_spark_api.core.projects.models import Project
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.entities import ErrorResponse
from app_spark_api.infras.accounts.auth import authenticated_user, login_required
from app_spark_api.repository.git import services
from app_spark_api.repository.git.entities import GitRepositoryResponse
from app_spark_api.repository.git.exceptions import GitRepositoryNotReadyError
from app_spark_api.repository.git.factory import get_repo_server_config
from app_spark_api.repository.git.models import ProjectGitRepository

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router(tags=["git-repositories"], auth=login_required)

PROJECT_ID = Path(..., description="项目 ID")


@router.get(
    "",
    response={HTTPStatus.OK: GitRepositoryResponse, HTTPStatus.NOT_FOUND: ErrorResponse},
    url_name="git-repository-retrieve",
    summary="查看 Project 的 Git 仓库状态",
)
async def get_git_repository(request: HttpRequest, project_id: str = PROJECT_ID):
    """仓库状态，不含 token 明文。尚未建仓时 404。"""
    project = await _get_project(request, project_id)
    try:
        repo = await ProjectGitRepository.objects.aget(project=project)
    except ProjectGitRepository.DoesNotExist:
        return Status(HTTPStatus.NOT_FOUND, {"detail": "This project has no Git repository."})
    return _to_response(repo)


@router.post(
    "provision/",
    response={
        HTTPStatus.OK: GitRepositoryResponse,
        HTTPStatus.CONFLICT: ErrorResponse,
    },
    url_name="git-repository-provision",
    summary="为 Project 补建或重试 Git 仓库",
)
async def provision_git_repository(request: HttpRequest, project_id: str = PROJECT_ID):
    """已有 Project 的显式建仓入口，也用于上次失败后的重试。"""
    project = await _get_project(request, project_id)
    repo = await services.aprovision_project_repository(project)
    return _to_response(repo)


@router.post(
    "revoke-credentials/",
    response={
        HTTPStatus.OK: GitRepositoryResponse,
        HTTPStatus.CONFLICT: ErrorResponse,
        HTTPStatus.NOT_FOUND: ErrorResponse,
    },
    url_name="git-repository-revoke",
    summary="撤销 Project 的 Git 仓库 token（应急）",
)
async def revoke_git_credentials(request: HttpRequest, project_id: str = PROJECT_ID):
    """生命周期与应急操作：凭据泄露、仓库归档。不在每轮对话里调用。"""
    project = await _get_project(request, project_id)
    try:
        repo = await services.arevoke_project_credentials(project)
    except GitRepositoryNotReadyError:
        return Status(HTTPStatus.NOT_FOUND, {"detail": "This project has no Git repository."})
    return _to_response(repo)


async def _get_project(request: HttpRequest, project_id: str) -> Project:
    user = authenticated_user(request)
    return await aget_object_or_404(
        Project.objects.owned_by(user.pk, tenant_id=get_tenant(user).id),
        id=project_id,
    )


def _to_response(repo: ProjectGitRepository) -> GitRepositoryResponse:
    return GitRepositoryResponse.from_repository(repo, commit=get_repo_server_config().commit_identity())
