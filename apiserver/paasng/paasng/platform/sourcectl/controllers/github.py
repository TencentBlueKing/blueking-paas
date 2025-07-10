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

import logging
import shutil
from os import PathLike, path, walk
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zipfile import ZipFile

import arrow
from django.utils.functional import cached_property

from paasng.platform.sourcectl import exceptions
from paasng.platform.sourcectl.github.client import GitHubApiClient
from paasng.platform.sourcectl.models import (
    AlternativeVersion,
    CommitInfo,
    CommitLog,
    GitProject,
    Repository,
    VersionInfo,
)
from paasng.platform.sourcectl.repo_controller import BaseGitRepoController
from paasng.platform.sourcectl.source_types import get_sourcectl_names
from paasng.platform.sourcectl.utils import generate_temp_file

logger = logging.getLogger(__name__)


class GitHubRepoController(BaseGitRepoController):
    def __init__(self, api_url: str, repo_url: str, user_credentials: Optional[Dict] = None):
        super().__init__(api_url, repo_url, user_credentials)
        self.api_client = GitHubApiClient(api_url=api_url, **(user_credentials or {}))
        self.repo_url = repo_url or ""

    def get_client(self):
        return self.api_client

    @cached_property
    def project(self) -> GitProject:
        """根据 repo_url 构建 GitProject 对象（GitHub）"""
        if not self.repo_url:
            raise ValueError("Git project with empty repo url")
        return GitProject.parse_from_repo_url(self.repo_url, get_sourcectl_names().GitHub)

    @classmethod
    def list_all_repositories(cls, **kwargs) -> List[Repository]:
        """返回当前 RepoController 可以控制的所有仓库列表"""
        api_client = GitHubApiClient(**kwargs)
        return [
            Repository(
                namespace=repo["owner"]["login"],
                project=repo["name"],
                description=repo["description"],
                # GitHub 未支持项目图标链接
                avatar_url="",
                web_url=repo["html_url"],
                http_url_to_repo=repo["clone_url"],
                ssh_url_to_repo=repo["ssh_url"],
                created_at=arrow.get(repo["created_at"]).datetime,
                last_activity_at=arrow.get(repo["updated_at"]).datetime,
            )
            for repo in api_client.list_repo()
        ]

    def touch(self) -> bool:
        try:
            self.list_alternative_versions()
        except (exceptions.RemoteResourceNotFoundError, exceptions.AccessTokenForbidden) as e:
            raise exceptions.AccessTokenForbidden(project=self.project) from e
        else:
            return True

    def export(self, local_path: PathLike, version_info: VersionInfo):
        """下载 zip 包并解压到指定路径"""
        target_branch, revision = self.extract_version_info(version_info)
        with generate_temp_file(suffix=".zip") as zip_file:
            self.api_client.repo_archive(self.project, zip_file, ref=revision or target_branch)
            ZipFile(zip_file, "r").extractall(local_path)

        # Github 下载的 zip 包比较特殊，外层有格式为 {username}-{proj_name}-{ref} 的目录，需要平铺开
        for root, dirs, _ in walk(str(local_path)):
            for name in dirs:
                if "." in name or name.startswith("/"):
                    continue
                if name.startswith(self.project.namespace):
                    src_dir = path.join(root, name)
                    logger.info("copy dir %s's content to dir %s during export github repo", src_dir, local_path)
                    shutil.copytree(src_dir, local_path, dirs_exist_ok=True)
                    shutil.rmtree(src_dir)

        return local_path

    def list_alternative_versions(self) -> List[AlternativeVersion]:
        """列举仓库所有可用 branch 或 tag"""
        result = []
        for branch in self.api_client.repo_list_branches(self.project):
            result.append(self._branch_data_to_version("branch", branch))
        for tag in self.api_client.repo_list_tags(self.project):
            result.append(self._branch_data_to_version("tag", tag))
        return result

    def extract_smart_revision(self, smart_revision: str) -> str:
        """解析组合 revision 信息（如 branch:master, tag:v1.2），获取更加具体的 commit id（hash）"""
        if ":" not in smart_revision:
            return smart_revision
        _, version_name = smart_revision.split(":")
        commit = self.api_client.repo_last_commit(self.project, version_name)
        return commit["sha"]

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        return version_info.version_name, version_info.revision

    def build_url(self, version_info: VersionInfo) -> str:
        return self.repo_url

    def build_compare_url(self, from_revision: str, to_revision: str) -> str:
        """构建比较链接，这里利用 Github 原生 diff 功能（基于 commit id 的比较）"""
        repo_url = self.repo_url
        from_revision = self.extract_smart_revision(from_revision)
        to_revision = self.extract_smart_revision(to_revision)
        return repo_url.replace(".git", f"/compare/{from_revision}...{to_revision}")

    def get_diff_commit_logs(self, from_revision, to_revision=None, rel_filepath=None) -> List[CommitLog]:
        """github 不支持该功能"""
        raise NotImplementedError

    def commit_files(self, commit_info: CommitInfo) -> None:
        """github 不支持该功能"""
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

    def download_directory(self, source_dir: str, local_path: Path) -> Path:
        """下载指定目录到本地

        :param source_dir: 代码仓库的指定目录
        :param local_path: 本地路径
        """
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

    def read_file(self, file_path: str, version_info: VersionInfo) -> bytes:
        """从当前仓库指定版本（version_info）的代码中读取指定文件（file_path）的内容"""
        target_branch, revision = self.extract_version_info(version_info)
        return self.api_client.repo_get_raw_file(self.project, file_path, ref=revision or target_branch)

    def _branch_data_to_version(self, data_source: str, data: Dict) -> AlternativeVersion:
        """将 branch / tag 信息转换成 AlternativeVersion

        :param data_source: tag / branch
        :param data: github api 请求结果
        """
        if data_source not in ("tag", "branch"):
            raise ValueError("type must be tag or branch")

        # NOTE Github API 不提供最后更新信息
        return AlternativeVersion(
            name=data["name"],
            type=data_source,
            revision=data["commit"]["sha"],
            url=data["commit"]["url"],
        )
