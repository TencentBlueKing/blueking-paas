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

import base64
import datetime
import logging
import pathlib
from typing import Dict, Generator, List, Optional, Union
from urllib.parse import urljoin

import arrow
import requests
from django.utils.translation import gettext_lazy as _

from paasng.infras.accounts.models import Oauth2TokenHolder
from paasng.platform.sourcectl import exceptions
from paasng.platform.sourcectl.client import DEFAULT_REPO_REF, DEFAULT_TIMEOUT, BaseGitApiClient
from paasng.platform.sourcectl.models import CommitInfo, GitProject

logger = logging.getLogger(__name__)


class GitHubApiClient(BaseGitApiClient):
    """Github API SDK"""

    def __init__(self, api_url: str, **kwargs):
        self.api_url = api_url
        self.session = requests.session()

        if "oauth_token" not in kwargs:
            raise exceptions.AccessTokenMissingError("oauth_token required")

        self.access_token = kwargs["oauth_token"]

        self.session.headers.update(
            {
                "Authorization": f"token {self.access_token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        self.token_holder: Optional[Oauth2TokenHolder] = kwargs.get("__token_holder")

    def list_repo(self, **kwargs) -> List[Dict]:
        """从 Github API 获取用户的所有仓库
        https://docs.github.com/en/rest/repos/repos#list-repositories-for-the-authenticated-user
        """
        return list(self._fetch_all_items(urljoin(self.api_url, "user/repos")))

    def repo_get_raw_file(self, project: GitProject, filepath: str, ref=DEFAULT_REPO_REF, **kwargs) -> bytes:
        """从远程仓库下载 filepath 的文件
        https://docs.github.com/en/rest/repos/contents#get-repository-content
        """
        url = urljoin(self.api_url, f"repos/{project.path_with_namespace}/contents/{filepath}")
        resp = self._request_with_retry(url, params={"ref": ref})
        if not resp or resp.get("encoding") != "base64":
            raise exceptions.UnsupportedGitRepoEncode(_("当前仅支持 base64 编码格式"))

        return base64.b64decode(resp["content"])

    def repo_list_branches(self, project: GitProject, **kwargs) -> List[Dict]:
        """获取指定仓库所有的 branch
        https://docs.github.com/en/rest/branches/branches#list-branches
        """
        url = urljoin(self.api_url, f"repos/{project.path_with_namespace}/branches")
        return list(self._fetch_all_items(url))

    def repo_list_tags(self, project: GitProject, **kwargs) -> List[Dict]:
        """获取指定仓库所有 tags
        https://docs.github.com/en/rest/repos/repos#list-repository-tags
        """
        url = urljoin(self.api_url, f"repos/{project.path_with_namespace}/tags")
        return list(self._fetch_all_items(url))

    def repo_archive(self, project: GitProject, local_path: pathlib.Path, ref: str = DEFAULT_REPO_REF) -> pathlib.Path:
        """下载 repo 压缩包（zip）到 local_path
        https://docs.github.com/en/rest/repos/contents#download-a-repository-archive-zip
        """
        url = urljoin(self.api_url, f"repos/{project.path_with_namespace}/zipball/{ref}")
        resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            raise exceptions.DownloadGitZipBallError(f"download git zip failed：{resp.reason}")

        local_path.write_bytes(resp.content)
        return local_path

    def repo_last_commit(self, project: GitProject, branch_or_hash: Optional[str] = None) -> Dict:
        """获取最后一次 commit 信息
        https://docs.github.com/en/rest/commits/commits#get-a-commit
        https://docs.github.com/en/rest/commits/commits#list-commits
        """
        owner_repo = project.path_with_namespace
        if branch_or_hash:
            url = urljoin(self.api_url, f"repos/{owner_repo}/commits/{branch_or_hash}")
            return self._request_with_retry(url)
        url = urljoin(self.api_url, f"repos/{owner_repo}/commits")
        return self._request_with_retry(url)[0]

    def get_user_info(self, username: str) -> Dict:
        """根据用户名查询用户信息
        https://docs.github.com/en/rest/users/users#get-a-user
        """
        return self._request_with_retry(urljoin(self.api_url, f"users/{username}"))

    def get_project_info(self, project: GitProject) -> Dict:
        """获取项目详细信息
        https://docs.github.com/en/rest/repos/repos#get-a-repository
        """
        url = urljoin(self.api_url, f"repos/{project.path_with_namespace}")
        return self._request_with_retry(url)

    def list_all_commit_logs(self, project: GitProject) -> Generator[Dict, None, None]:
        """获取全量 commit 信息
        https://docs.github.com/en/rest/commits/commits#list-commits
        """
        url = urljoin(self.api_url, f"repos/{project.path_with_namespace}/commits")
        for c in self._fetch_all_items(url):
            yield {
                "id": c["sha"],
                # GitHub commit 信息无 short_id && title，使用 hash，message 替换
                "short_id": c["sha"],
                "title": c["commit"]["message"],
                "author_name": c["commit"]["author"]["name"],
                "author_email": c["commit"]["author"]["email"],
                # 类型转换, 从字符串转为 datetime
                "committed_date": arrow.get(c["commit"]["author"]["date"]).datetime,
                "message": c["commit"]["message"],
            }

    def calculate_user_contribution(
        self,
        username: str,
        project: GitProject,
        begin_date: Optional[Union[datetime.datetime, arrow.Arrow]] = None,
        end_date: Optional[Union[datetime.datetime, arrow.Arrow]] = None,
    ) -> Dict:
        """GitHub 暂不支持统计贡献"""
        return {
            "project_total_lines": "unsupported",
            "user_total_lines": "unsupported",
            "project_commit_nums": "unsupported",
            "user_commit_nums": "unsupported",
        }

    def commit_files(self, project: GitProject, commit_info: CommitInfo) -> Dict:
        """批量提交修改文件"""
        raise NotImplementedError("GitHub don't support batch commit currently")
