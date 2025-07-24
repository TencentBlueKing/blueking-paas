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
from collections import Counter
from typing import Dict, Generator, List

import arrow
import gitlab
from gitlab.exceptions import GitlabGetError
from gitlab.v4.objects import ProjectFile

from paasng.platform.sourcectl.exceptions import ReadFileNotFoundError
from paasng.platform.sourcectl.models import GitProject


class GitLabApiClient:
    def __init__(self, api_url, username=None, password=None, **kwargs):
        self.gl = gitlab.Gitlab(
            api_url,
            http_username=username,
            http_password=password,
            private_token=kwargs.get("private_token"),
            oauth_token=kwargs.get("oauth_token"),
        )
        self.gl.auth()

    def list_repo(self, visibility="private") -> List[ProjectFile]:
        """从远程服务器获取当前用户的所有仓库
        visibility:
            private:    Project access must be granted explicitly for each user.
            internal:   The project can be cloned by any logged in user.
            public:     The project can be cloned without any authentication.
        """
        return self.gl.projects.list(all=True, visibility=visibility)

    def get_project_info(self, project):
        """尝试访问远程仓库, 试探是否有访问权限"""
        return self.gl.projects.get(project.path_with_namespace)

    def repo_get_raw_file(self, project: GitProject, file_path, ref="master", **kwargs) -> bytes:
        """
        从远程仓库下载 file_path 的文件

        :param project: 项目对象
        :param file_path: 需要下载的文件路径
        :param ref: branch 或 commit 的 hash 值
        :return: 文件内容 bytes 类型
        """
        project_obj = self.gl.projects.get(project.path_with_namespace)
        try:
            file = project_obj.files.get(file_path=file_path, ref=ref)
        except GitlabGetError:
            raise ReadFileNotFoundError(f"file: {file_path} not found")
        return base64.b64decode(file.attributes["content"])

    def repo_list_branches(self, project: GitProject, **kwargs) -> List[dict]:
        """
        获取仓库的所有 branches
        :param project: 项目对象
        :return: 包含 branch 字典的列表，具体内容看 gitlab 文档
        """
        project_obj = self.gl.projects.get(project.path_with_namespace)
        return [branch.attributes for branch in project_obj.branches.list(all=True)]

    def repo_list_tags(self, project: GitProject, **kwargs) -> List[dict]:
        """
        获取仓库的所有 tags
        :param project: 项目对象
        :return: 包含 tag 字典的列表，具体内容看 gitlab 文档
        """
        project_obj = self.gl.projects.get(project.path_with_namespace)
        return [tag.attributes for tag in project_obj.tags.list(all=True)]

    def repo_compare(self, project: GitProject, from_revision, to_revision) -> dict:
        """
        对比 from_revision 和 to_revision 两次 commit 之间的差异
        :param project: 项目对象
        :param from_revision: commit_hash_1
        :param to_revision: commit_hash_2
        :return: 包含 compare 内容的字典，具体内容看 gitlab 文档
        """
        project_obj = self.gl.projects.get(project.path_with_namespace)
        compare = project_obj.repository_compare(from_revision, to_revision)
        return compare

    def list_all_commit_logs(self, project: GitProject) -> Generator[Dict, None, None]:
        """获取项目至今的所有 commit 日志
        :param project: 项目对象
        """
        project_obj = self.gl.projects.get(project.path_with_namespace)
        for commit in project_obj.commits.list(all=True):
            yield {
                "id": commit.id,
                "short_id": commit.short_id,
                "title": commit.title,
                # 由于工蜂没有`committer_name`字段, 因此统一使用 `author_name`
                "author_name": commit.author_name,
                "author_email": commit.author_email,
                # 类型转换, 从字符串转为 datetime
                "committed_date": arrow.get(commit.committed_date).datetime,
                "message": commit.message,
            }

    def repo_contributors(self, project: GitProject) -> List[dict]:
        project_obj = self.gl.projects.get(project.path_with_namespace)
        result = project_obj.repository_contributors()
        # TODO: 建模
        return result

    def repo_last_commit(self, project: GitProject, branch_or_hash=None) -> dict:
        """
        获取最后一次 commit 的内容
        :param project: 项目对象
        :param branch_or_hash: 分支名或 commit 的hash值
        :return: 包含 commit 内容的字典，具体内容看 gitlab 文档
        """
        project_obj = self.gl.projects.get(project.path_with_namespace)
        if branch_or_hash:
            return project_obj.commits.get(branch_or_hash).attributes
        return project_obj.commits.list(per_page=1)[0].attributes

    def repo_archive(self, project: GitProject, local_path, ref) -> str:
        """
        下载 repo 的压缩包 到 local_path 里
        :param project: 项目对象
        :param local_path: 将 repo 写进去本地目录
        :param ref: 分支信息, 可以是 branch, tags, hash
        :return: local_path
        """
        project_obj = self.gl.projects.get(project.path_with_namespace)
        tgz = project_obj.repository_archive(sha=ref)
        with open(local_path, "wb") as fh:
            fh.write(tgz)
        return local_path

    @property
    def user(self):
        return self.gl.user

    def calculate_user_contribution(self, username: str, project: GitProject):
        """
        统计用户在项目里的贡献度
        :param username:
        """
        gitlab_project = self.gl.projects.get(project.path_with_namespace)
        all_commits = gitlab_project.commits.list(all=True, with_stats=True)
        # 内存里过滤可以拿到用户在项目里提交的 commit 数量
        project_total_lines = len(all_commits)
        user_commit_nums = 0
        # 项目首次提交时间
        project_first_commit_date = arrow.get().date()
        # 用户首次提交时间
        user_first_commit_date = arrow.get().date()
        # 项目总代码行数.....
        project_commit_nums = 0
        # 用户提交的总代码行数.....
        user_total_lines = 0

        for commit in all_commits:
            committed_date = arrow.get(commit.committed_date).date()
            project_commit_nums += commit.stats["additions"]
            project_commit_nums -= commit.stats["deletions"]
            project_first_commit_date = min(project_first_commit_date, committed_date)
            if commit.author_name == username:
                user_commit_nums += 1
                user_total_lines += commit.stats["additions"]
                user_total_lines -= commit.stats["deletions"]
                user_first_commit_date = min(user_first_commit_date, committed_date)

        return dict(
            project_total_lines=project_total_lines,
            user_total_lines=user_total_lines,
            project_commit_nums=project_commit_nums,
            user_commit_nums=user_commit_nums,
        )

    def calculate_user_commit_calendar(self, username: str, project: GitProject) -> Counter:
        # 用户 commit 日历
        user_commit_calendar: Counter = Counter()
        for commit in self.list_all_commit_logs(project):
            if commit["author_name"] == username:
                user_commit_calendar[commit["committed_date"].date()] += 1
        return user_commit_calendar
