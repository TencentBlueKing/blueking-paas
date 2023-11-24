# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import arrow
from blue_krill.data_types.url import MutableURL
from django.utils.functional import cached_property

from paasng.platform.sourcectl import exceptions
from paasng.platform.sourcectl.git.client import GitClient
from paasng.platform.sourcectl.gitee.client import GiteeApiClient
from paasng.platform.sourcectl.models import AlternativeVersion, CommitLog, GitProject, Repository, VersionInfo
from paasng.platform.sourcectl.repo_controller import BaseGitRepoController
from paasng.platform.sourcectl.source_types import get_sourcectl_names

logger = logging.getLogger(__name__)


class GiteeRepoController(BaseGitRepoController):
    def __init__(self, api_url: str, repo_url: str, user_credentials: Optional[Dict] = None):
        super().__init__(api_url, repo_url, user_credentials)
        self.user_credentials = user_credentials or {}
        self.repo_url = repo_url or ""
        self.api_client = GiteeApiClient(api_url=api_url, **(self.user_credentials))

    def get_client(self):
        return self.api_client

    @cached_property
    def project(self) -> GitProject:
        """根据 repo_url 构建 GitProject 对象（Gitee）"""
        if not self.repo_url:
            raise ValueError("Git project with empty repo url")
        return GitProject.parse_from_repo_url(self.repo_url, get_sourcectl_names().Gitee)

    @classmethod
    def list_all_repositories(cls, **kwargs) -> List[Repository]:
        """返回当前 RepoController 可以控制的所有仓库列表"""
        api_client = GiteeApiClient(**kwargs)
        return [
            Repository(
                namespace=repo["namespace"]["path"],
                project=repo["name"],
                description=repo["description"],
                # Gitee 未支持项目图标链接
                avatar_url="",
                web_url=repo["html_url"],
                http_url_to_repo=repo["html_url"],
                ssh_url_to_repo=repo["ssh_url"],
                created_at=arrow.get(repo["created_at"]).datetime,
                last_activity_at=arrow.get(repo["updated_at"]).datetime,
            )
            for repo in api_client.list_repo()
        ]

    def touch(self) -> bool:
        try:
            self.list_alternative_versions()
            return True
        except (exceptions.DoesNotExistsOnGitServer, exceptions.AccessTokenForbidden) as e:
            raise exceptions.AccessTokenForbidden(project=self.project) from e

    def export(self, local_path, version_info: VersionInfo):
        """Gitee API 不支持下载压缩包，改成直接将代码库 clone 下来，由通用逻辑进行打包"""
        git_client = GitClient()
        git_client.clone(self._build_repo_url_with_auth(), local_path, branch=version_info.version_name, depth=1)
        git_client.clean_meta_info(local_path)

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
        version_type, version_name = smart_revision.split(":")
        commit = self.api_client.repo_last_commit(self.project, version_name)
        return commit["sha"]

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        return version_info.version_name, version_info.revision

    def build_url(self, version_info: VersionInfo) -> str:
        return self.repo_url

    def build_compare_url(self, from_revision: str, to_revision: str) -> str:
        """构建比较链接，这里利用 Gitee 原生 diff 功能（基于 commit id 的比较）"""
        repo_url = self.repo_url
        from_revision = self.extract_smart_revision(from_revision)
        to_revision = self.extract_smart_revision(to_revision)
        return repo_url.replace(".git", f"/compare/{from_revision}...{to_revision}")

    def get_diff_commit_logs(self, from_revision, to_revision=None, rel_filepath=None) -> List[CommitLog]:
        """gitee 不支持该功能"""
        raise NotImplementedError

    def read_file(self, file_path: str, version_info: VersionInfo) -> bytes:
        """从当前仓库指定版本（version_info）的代码中读取指定文件（file_path）的内容"""
        target_branch, revision = self.extract_version_info(version_info)
        return self.api_client.repo_get_raw_file(self.project, file_path, ref=revision or target_branch)

    def _branch_data_to_version(self, data_source: str, data: Dict) -> AlternativeVersion:
        """将 branch / tag 信息转换成 AlternativeVersion

        :param data_source: tag / branch
        :param data: gitee api 请求结果
        """
        if data_source not in ("tag", "branch"):
            raise ValueError("type must be tag or branch")

        # NOTE Gitee API 不提供最后更新信息
        return AlternativeVersion(
            name=data["name"],
            type=data_source,
            revision=data["commit"]["sha"],
            url=data["commit"]["url"],
        )

    def _build_repo_url_with_auth(self) -> MutableURL:
        """构建包含 username:oauth_token 的 repo url"""
        oauth_token = self.user_credentials.get("oauth_token")
        if not oauth_token:
            raise exceptions.AccessTokenMissingError("oauth_token required")

        try:
            username = self.api_client.get_current_user()["login"]
        except Exception:
            logger.exception(
                "Can't get username from gitee, use namespace as fallback(only work for personal project)"
            )
            username = self.project.namespace

        return MutableURL(self.repo_url).replace(username=quote(username), password=quote(oauth_token))
