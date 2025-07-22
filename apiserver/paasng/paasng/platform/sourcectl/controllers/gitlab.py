# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import datetime
import shutil
from functools import wraps
from os import PathLike
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import arrow
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from gitlab.exceptions import GitlabAuthenticationError, GitlabGetError

from paasng.platform.sourcectl import exceptions
from paasng.platform.sourcectl.client import DEFAULT_REPO_REF
from paasng.platform.sourcectl.gitlab.client import GitLabApiClient
from paasng.platform.sourcectl.models import (
    AlternativeVersion,
    CommitInfo,
    CommitLog,
    DiffChange,
    GitProject,
    Repository,
    VersionInfo,
)
from paasng.platform.sourcectl.repo_controller import BaseGitRepoController
from paasng.platform.sourcectl.source_types import get_sourcectl_names
from paasng.platform.sourcectl.utils import generate_temp_file, uncompress_directory
from paasng.utils.text import remove_suffix


def error_converter(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except GitlabGetError as e:
            if e.response_code == 404:
                raise exceptions.RemoteResourceNotFoundError(e.error_message)
            raise exceptions.GitLabCommonError(e.error_message)
        except GitlabAuthenticationError as e:
            raise exceptions.AccessTokenForbidden from e

    return wrapper


def strftime_for_gitlab_project(datetime_str):
    return datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fz")


class GitlabRepoController(BaseGitRepoController):
    def __init__(self, api_url: str, repo_url: Optional[str] = None, user_credentials: Optional[Dict] = None):
        super().__init__(api_url, repo_url, user_credentials)
        self.api_client = GitLabApiClient(api_url=api_url, **(user_credentials or {}))
        self.repo_url = repo_url or ""

    def get_client(self):
        return self.api_client

    @cached_property
    def project(self) -> GitProject:
        # git 项目完整路径, 从 `http://git.example.com/namespace/[sub_group/]project-repo.git` 解析 `namespace` 和 `project_name`
        if not self.repo_url:
            raise ValueError("Unknown git project")
        return GitProject.parse_from_repo_url(self.repo_url, get_sourcectl_names().GitLab)

    @classmethod
    def list_all_repositories(cls, **kwargs) -> List[Repository]:
        """返回当前 RepoController 可以控制的所有仓库列表"""
        api_client = GitLabApiClient(**kwargs)
        return [
            Repository(
                namespace=project.namespace["name"],
                project=project.name,
                description=project.description,
                avatar_url=project.avatar_url,
                web_url=project.web_url,
                http_url_to_repo=project.http_url_to_repo,
                ssh_url_to_repo=project.ssh_url_to_repo,
                created_at=strftime_for_gitlab_project(project.created_at),
                last_activity_at=strftime_for_gitlab_project(project.last_activity_at),
            )
            for project in api_client.list_repo()
        ]

    def touch(self) -> bool:
        try:
            error_converter(self.api_client.get_project_info)(self.project)
        except (exceptions.RemoteResourceNotFoundError, exceptions.AccessTokenForbidden) as e:
            raise exceptions.AccessTokenForbidden(project=self.project) from e
        else:
            return True

    @error_converter
    def export(self, local_path: PathLike, version_info: VersionInfo | None = None, source_dir: str | None = None):
        """导出指定版本的整个项目内容或指定目录到本地路径

        :param local_path: 本地路径
        :param version_info: 可选，指定版本信息
        :param source_dir: 可选，指定要导出的子目录
        """
        if version_info:
            tag_or_branch, revision = self.extract_version_info(version_info)
            ref = revision or tag_or_branch
        else:
            ref = DEFAULT_REPO_REF

        with generate_temp_file(suffix=".tar.gz") as tar_file:
            self.api_client.repo_archive(self.project, tar_file, ref=ref)
            uncompress_directory(tar_file, local_path)

        # The extracted repo files was put in an extra sub-directory named "{repo}-{sha}/", So we
        # need to move the files in that directory into it's parent {local_path}
        local_path_obj = Path(local_path).absolute()
        wrapper_dir = list(local_path_obj.iterdir())[0].absolute()
        for child in wrapper_dir.iterdir():
            # Move all contents into it's parent
            shutil.move(str(child), str(local_path_obj))
        shutil.rmtree(str(wrapper_dir))

    @error_converter
    def list_alternative_versions(self) -> List[AlternativeVersion]:
        """仓库级: 罗列所有分支和标签"""
        pri_version_names = {"trunk": -1, "master": -1}
        result = []
        for branch in self.api_client.repo_list_branches(self.project):
            result.append(self._branch_data_to_version("branch", branch))
        for tag in self.api_client.repo_list_tags(self.project):
            result.append(self._branch_data_to_version("tag", tag))
        return sorted(result, key=lambda item: (pri_version_names.get(item.name, 0), item.last_update), reverse=True)

    @error_converter
    def extract_smart_revision(self, smart_revision: str) -> str:
        if ":" not in smart_revision:
            return smart_revision
        version_type, version_name = smart_revision.split(":")
        try:
            commit = self.api_client.repo_last_commit(self.project, version_name)
        except GitlabGetError as e:
            # 不能保证 bug 触发条件，所以触发之后再做判断
            # gitlab bug: https://gitlab.com/gitlab-org/gitlab-ce/issues/42231
            if e.response_code == 404 and e.error_message == "404 Commit Not Found" and "." in version_name:
                raise exceptions.GitLabBranchNameBugError(_("GitLab API 不支持名称包含 '.' 的分支，请修改分支名"))
            raise
        return commit["id"]

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        return version_info.version_name, version_info.revision

    def build_url(self, version_info: VersionInfo) -> str:
        # Always use base repo url for git repository
        return self.repo_url

    @error_converter
    def build_compare_url(self, from_revision: str, to_revision: str) -> str:
        repo_url = self.repo_url
        from_revision = self.extract_smart_revision(from_revision)
        to_revision = self.extract_smart_revision(to_revision)

        return remove_suffix(repo_url, ".git") + f"/compare/{from_revision}...{to_revision}"

    @error_converter
    def get_diff_commit_logs(self, from_revision, to_revision=None, rel_filepath=None) -> List[CommitLog]:
        to_revision = to_revision or from_revision
        compare = self.api_client.repo_compare(self.project, from_revision, to_revision)
        d = arrow.get(compare["commit"]["committed_date"]).to("utc").datetime
        return (
            [
                CommitLog(
                    message=compare["commit"]["message"],
                    revision=compare["commit"]["id"],
                    author=compare["commit"]["committer_name"],
                    date=d,
                    changelist=[DiffChange.format_from_gitlab(diff) for diff in compare["diffs"]],
                )
            ]
            if compare["commit"]
            else []
        )

    def commit_files(self, commit_info: CommitInfo) -> None:
        """gitlab 不支持该功能"""
        raise NotImplementedError

    def create_with_member(self, *args, **kwargs):
        """创建代码仓库并添加成员"""
        raise NotImplementedError

    def create_project(self, *args, **kwargs):
        """创建代码仓库"""
        raise NotImplementedError

    def delete_project(self, *args, **kwargs):
        """删除在 VCS 上的源码项目"""
        raise NotImplementedError

    def commit_and_push(
        self,
        local_path: Path,
        commit_message: str,
        commit_name: str | None = None,
        commit_email: str | None = None,
    ) -> None:
        """将本地文件目录提交并推送到远程仓库

        :param local_path: 本地文件所有路径
        :param commit_message: 提交信息
        :param commit_name: 提交人名称，不传则使用平台的默认值
        :param commit_email: 提交人邮箱，不传则使用平台的默认值
        """
        raise NotImplementedError

    @error_converter
    def read_file(self, file_path: str, version_info: VersionInfo) -> bytes:
        """从当前仓库指定版本(version_info)的代码中读取指定文件(file_path) 的内容"""
        tag_or_branch, revision = self.extract_version_info(version_info)
        return self.api_client.repo_get_raw_file(self.project, file_path, ref=revision or tag_or_branch)

    def _branch_data_to_version(self, data_source: str, data: Dict) -> AlternativeVersion:
        """[private] transform a git branch data to an AlternativeVersion object

        :param data_source: tag or branch
        :param data: JSON data returned from gitlab api
        """
        if data_source not in ("tag", "branch"):
            raise ValueError("type must be tag or branch")
        try:
            message = data["message"]
        except KeyError:
            message = data["commit"]["message"]

        date_str = data["commit"]["committed_date"]
        # Convert local time to utc datetime
        commit_date = arrow.get(date_str).to("utc").datetime
        return AlternativeVersion(
            name=data["name"],
            type=data_source,
            revision=data["commit"]["id"],
            url=self.repo_url,
            last_update=commit_date,
            message=message,
        )
