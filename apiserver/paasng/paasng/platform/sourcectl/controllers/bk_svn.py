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
import os
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from paasng.platform.sourcectl.exceptions import BasicAuthError
from paasng.platform.sourcectl.models import AlternativeVersion, CommitInfo, CommitLog, Repository, VersionInfo
from paasng.platform.sourcectl.svn.client import SvnRepositoryClient, svn_version_types
from paasng.platform.sourcectl.svn.server_config import get_bksvn_config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


class SvnRepoController:
    def __init__(self, repo_url, repo_admin_credentials=None):
        self.repo_url = repo_url
        self.svn_client = SvnRepositoryClient(repo_url=repo_url, **repo_admin_credentials)

    def get_client(self):
        return self.svn_client

    @classmethod
    def init_by_module(cls, module: "Module", operator: Optional[str] = None):
        repo_url = module.get_source_obj().get_repo_url()
        repo_admin_credentials = get_bksvn_config(name=module.source_type).get_admin_credentials()
        return cls(repo_url=repo_url, repo_admin_credentials=repo_admin_credentials)

    @classmethod
    def init_by_server_config(cls, source_type: str, repo_url: str):
        """Return a RepoController object from given source_type

        :param source_type: Code repository type, such as github
        :param repo_url: repository url
        """
        raise NotImplementedError

    @classmethod
    def list_all_repositories(cls, **kwargs) -> List[Repository]:
        """返回当前 RepoController 可以控制的所有仓库列表"""
        raise NotImplementedError

    def touch(self) -> bool:
        try:
            self.svn_client.rclient.info()
        except Exception as e:
            if "E170001" in str(e):
                raise BasicAuthError()
            raise
        else:
            return True

    def export(self, local_path: PathLike, version_info: VersionInfo | None = None):
        """导出指定版本下的所有内容到指定目录

        :param local_path: 本地路径
        :param version_info: 可选，指定版本信息
        """
        if version_info:
            target_branch, revision = self.extract_version_info(version_info)
        else:
            target_branch, revision = "trunk", None
        self.svn_client.export(target_branch, local_path=local_path, revision=revision)

    def list_alternative_versions(self) -> List[AlternativeVersion]:
        try:
            return self.svn_client.list_alternative_versions()
        except Exception:
            logger.exception(f"Unable to list alternative versions for {self.repo_url}")
            return []

    def extract_smart_revision(self, smart_revision: str) -> str:
        # WARNING: 检查下面这行代码的正确性，类型错误：Invalid index type "str" for "str"
        return self.svn_client.extract_smart_revision(smart_revision)["commit_revision"]  # type: ignore

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        if version_info.version_type == "trunk":
            return "trunk", version_info.revision
        else:
            version = svn_version_types.get_version_by_type(version_info.version_type)
            if not version:
                raise RuntimeError(f"no svn version found for type: {version_info.version_type}")
            return version.get_rel_path(version_info.version_name), version_info.revision

    def build_url(self, version_info: VersionInfo) -> str:
        base_url = self.repo_url.rstrip("/")
        if version_info.version_type == "trunk":
            return f"{base_url}/{version_info.version_type}"
        else:
            return f"{base_url}/{version_info.version_type}/{version_info.version_name}"

    def build_compare_url(self, from_revision, to_revision):
        """由子类实现，获取外部系统的源码差异对比的链接"""
        raise NotImplementedError

    def get_diff_commit_logs(self, from_revision, to_revision=None, rel_filepath=None) -> List[CommitLog]:
        return [
            CommitLog(commit["message"], commit["revision"], commit["date"], commit["author"], commit["changelist"])
            for commit in self.svn_client.get_commit_logs(from_revision, to_revision, rel_filepath)
        ]

    def commit_files(self, commit_info: CommitInfo) -> None:
        """bk_svn 不支持该功能"""
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
        """从当前仓库指定版本(version_info)的代码中读取指定文件(file_path) 的内容"""
        target_branch, revision = self.extract_version_info(version_info)
        return self.svn_client.read_file(os.path.join(target_branch, file_path), revision)
