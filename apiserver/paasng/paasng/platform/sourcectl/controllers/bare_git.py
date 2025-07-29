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
import operator
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, Iterator, List, Optional, Tuple
from urllib.parse import quote, urlparse

from blue_krill.data_types.url import MutableURL
from django.core.exceptions import ObjectDoesNotExist

from paasng.platform.sourcectl.exceptions import (
    BasicAuthError,
    ReadFileNotFoundError,
    ReadLinkFileOutsideDirectoryError,
)
from paasng.platform.sourcectl.models import AlternativeVersion, CommitInfo, CommitLog, Repository, VersionInfo
from paasng.platform.sourcectl.repo_controller import BaseGitRepoController
from paasng.platform.sourcectl.utils import generate_temp_dir

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module
    from paasng.platform.sourcectl.models import RepositoryInstance

from paasng.platform.sourcectl.git.client import GitClient, GitCommandExecutionError, Ref

logger = logging.getLogger(__name__)


class BareGitRepoController(BaseGitRepoController):
    """Git 协议仓库控制器"""

    def __init__(self, repo_url: str, repo_obj: "RepositoryInstance"):
        self.repo_url = MutableURL(repo_url)
        self.repo_obj = repo_obj
        self.client = GitClient()

    @classmethod
    def init_by_module(cls, module: "Module", operator: Optional[str] = None) -> "BareGitRepoController":
        repo_obj = module.get_source_obj()
        repo_url = repo_obj.get_repo_url()
        if not repo_url:
            raise ValueError("Require repo_url to init GeneralGitRepoController")

        from paasng.platform.sourcectl.models import RepoBasicAuthHolder

        try:
            holder = RepoBasicAuthHolder.objects.get_by_repo(module, repo_obj)
        except ObjectDoesNotExist:
            logger.warning("repo<%s> has no basic auth, maybe missing", repo_obj.get_identity())
            return cls(repo_url=repo_url, repo_obj=repo_obj)

        # 当前 BareGit 只支持 basic auth
        o = urlparse(repo_url)
        repo_url_with_auth = (
            f"{o.scheme}://{quote(holder.basic_auth.username)}:{quote(holder.basic_auth.password)}@{o.netloc}{o.path}"
        )
        return cls(repo_url=repo_url_with_auth, repo_obj=repo_obj)

    @classmethod
    def list_all_repositories(cls, api_url: str, user_credentials: Dict) -> List[Repository]:
        """返回当前 RepoController 可以控制的所有仓库列表"""
        raise NotImplementedError

    def touch(self) -> bool:
        """检查仓库权限"""
        try:
            # 使用 ls-remote 来提速
            self.client.list_remote_raw(self.repo_url)
        except GitCommandExecutionError as e:
            if "authentication failed" in str(e).lower():
                raise BasicAuthError("wrong username or password")

            logger.exception("Failed to access the remote git repo, command error.")
            raise
        except Exception:
            logger.exception("Failed to access the remote git repo, reason unknown.")
            raise
        return True

    def export(self, local_path: PathLike, version_info: VersionInfo | None = None):
        """导出指定版本下的所有内容到指定目录

        :param local_path: 本地路径
        :param version_info: 可选，指定版本信息
        """
        branch = version_info.version_name if version_info else None

        local_path = Path(local_path)
        self.client.clone(self.repo_url, local_path, depth=1, branch=branch)
        self.client.clean_meta_info(local_path)

    def list_alternative_versions(self) -> List[AlternativeVersion]:
        """尝试直接从远端获取可选的分支信息"""
        with generate_temp_dir() as temp_dir:
            # Use "blob-less" cloning for faster speed.
            #
            # NOTE: We should consider getting branches and tags using the "ls-remote"
            # command to avoid any form of cloning. But there is still a problem with
            # "ls-remote": We can't get commit time and message without cloning the repo.
            self.client.clone_no_blob(self.repo_url, temp_dir)
            return sorted(
                self.transfer_refs_to_versions(self.client.list_refs(temp_dir)),
                key=operator.attrgetter("last_update"),
                reverse=True,
            )

    @staticmethod
    def transfer_refs_to_versions(refs: Iterator[Ref]) -> Generator[AlternativeVersion, None, None]:
        """将远端拉取到的 ref 转换成可理解的 Version 列表"""
        for ref in refs:
            yield AlternativeVersion(
                name=ref.name,
                revision=ref.commit_id,
                last_update=ref.commit_time,
                type=ref.type,
                message=ref.message,
                url="",
            )

    def extract_smart_revision(self, smart_revision: str) -> str:
        """将有名字的版本号（Named Version）转换成更具体的版本号, 例如，将 Git 的 master 分支转换成 SHA Commit ID

        :param smart_revision: 有名字的版本号，比如 master
        """
        raise NotImplementedError

    def extract_version_info(self, version_info: VersionInfo) -> Tuple[str, str]:
        """[private] 将 version_info 转换成 version_name 和 revision"""
        logger.debug("version_name: %s, revision: %s", version_info.version_name, version_info.revision)
        return version_info.version_name, version_info.revision

    def build_url(self, version_info: VersionInfo) -> str:
        # self.repo_url 包含了 basic auth 信息，这里不能直接暴露
        return self.repo_obj.get_repo_url() or ""

    def build_compare_url(self, from_revision: str, to_revision: str) -> str:
        """裸 GitServer 无法支持差异比较页面"""
        raise NotImplementedError

    def get_diff_commit_logs(self, from_revision, to_revision, rel_filepath=None) -> List[CommitLog]:
        raise NotImplementedError

    def commit_files(self, commit_info: CommitInfo) -> None:
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

    def read_file(self, file_path, version_info: VersionInfo) -> bytes:
        """读取目标文件"""
        with generate_temp_dir() as temp_dir:
            self.client.clone(self.repo_url, temp_dir, depth=1, branch=version_info.version_name)

            fp: Path = temp_dir / file_path
            if not fp.exists():
                raise ReadFileNotFoundError(f"{file_path} not exists.")
            try:
                fp.resolve().relative_to(temp_dir)
            except ValueError:
                raise ReadLinkFileOutsideDirectoryError()
            return fp.read_bytes()
