# -*- coding: utf-8 -*-
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

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple, Union

from blue_krill.data_types.url import MutableURL
from django.utils.encoding import force_str

from paasng.platform.sourcectl.exceptions import RequestTimeOutError
from paasng.utils.validators import validate_repo_url

logger = logging.getLogger(__name__)


class GitCommandExecutionError(Exception):
    """执行 git 命令时发生错误"""


class GitURLValidationError(GitCommandExecutionError):
    """Git 仓库 URL 安全校验失败"""


@dataclass
class Ref:
    name: str
    type: str
    commit_id: str
    commit_time: datetime
    message: str

    def __str__(self):
        return f"<{self.name} ({self.type}) {self.commit_id[:8]}>"


class GitCommand:
    """Git 命令封装。

    :param args: Git 子命令选项参数，位于 ``--`` 之前。
    :param end_of_options_args: ``--`` 之后的参数（URL、路径、分支名等），
        这些参数不会被 git 解释为选项，即使它们以 ``-`` 开头。
        构建命令时会自动在前面插入 ``--`` 分隔符。
    """

    def __init__(
        self,
        git_filepath: str,
        command: str,
        args: List[str] | None = None,
        end_of_options_args: List[str] | None = None,
        cwd: str = "",
        envs: Optional[Dict] = None,
    ):
        self.git_filepath = git_filepath
        self.command = command
        self.args = args or []
        self.end_of_options_args = end_of_options_args or []
        self.cwd = cwd
        self.envs = envs or {}

    def to_cmd(self, obscure: bool = False) -> List[str]:
        cmd = [self.git_filepath, self.command, *self.args]
        if self.end_of_options_args:
            cmd.append("--")
            cmd.extend(self.end_of_options_args)
        return cmd

    def get_sensitive_texts(self) -> List[str]:
        """Get sensitive texts in the current command, the texts must not be displayed
        to the user or written to the logs.
        """
        return []

    def __str__(self):
        return " ".join(self.to_cmd(obscure=True))


class GitCloneCommand(GitCommand):
    def __init__(
        self,
        git_filepath: str,
        repository: MutableURL,
        target_directory: str = ".",
        args: Optional[List[str]] = None,
        cwd: str = "",
        envs: Optional[Dict] = None,
    ):
        """
        Name
               git-clone - Clone a repository into a new directory
        SYNOPSIS
               git clone [--bare] [--] <repository> [<target_directory>]
        """
        super().__init__(git_filepath=git_filepath, command="clone", args=args, cwd=cwd, envs=envs)
        self.repository = repository
        self.target_directory = target_directory

    def to_cmd(self, obscure: bool = False) -> List[str]:
        """"""
        cmd = super().to_cmd(obscure=obscure)
        cmd.append("--")
        cmd.extend([str(self.repository.obscure()) if obscure else str(self.repository), self.target_directory])
        return cmd

    def get_sensitive_texts(self) -> List[str]:
        """Get sensitive texts in the current command, the texts must not be displayed
        to the user or written to the logs.
        """
        netloc = self.repository.netloc
        if not netloc:
            return []

        user_info, have_info, _ = netloc.rpartition("@")
        if not have_info:
            return []
        # Consider the user info as sensitive because it contains password
        return [user_info + "@"]


class GitFetchCommand(GitCommand):
    def __init__(
        self,
        git_filepath: str,
        repository: MutableURL,
        refspecs: List[str],
        args: Optional[List[str]] = None,
        cwd: str = "",
        envs: Optional[Dict] = None,
    ):
        """
        Name
               git-fetch - Download objects and refs from another repository
        SYNOPSIS
               git fetch [<options>] [--] <repository> [<refspec>...]
        """
        super().__init__(git_filepath=git_filepath, command="fetch", args=args, cwd=cwd, envs=envs)
        self.repository = repository
        self.refspecs = refspecs

    def to_cmd(self, obscure: bool = False) -> List[str]:
        cmd = super().to_cmd(obscure=obscure)
        cmd.append("--")
        cmd.extend([str(self.repository.obscure()) if obscure else str(self.repository), *self.refspecs])
        return cmd

    def get_sensitive_texts(self) -> List[str]:
        """Get sensitive texts in the current command, the texts must not be displayed
        to the user or written to the logs.
        """
        netloc = self.repository.netloc
        if not netloc:
            return []

        user_info, have_info, _ = netloc.rpartition("@")
        if not have_info:
            return []
        # Consider the user info as sensitive because it contains password
        return [user_info + "@"]


class GitClient:
    """Git 客户端"""

    META_GIT_DIR = ".git"
    _git_filepath = "git"
    _default_timeout = 600

    def checkout(self, path: Path, target: str) -> str:
        """切换分支或tag"""
        command = GitCommand(
            git_filepath=self._git_filepath, command="checkout", end_of_options_args=[target], cwd=str(path)
        )
        return self.run(command)

    def clone(
        self,
        url: Union[str, MutableURL],
        path: Path,
        envs: Dict | None = None,
        depth: int | None = None,
        branch: str | None = None,
    ) -> str:
        """克隆仓库

        :param url: 仓库地址
        :param path: 存储路径
        :param envs: 环境变量
        :param depth: 克隆深度
        :param branch: 克隆分支
        :return: 返回 clone 结果
        """
        args = []
        if depth is not None:
            args.extend(["--depth", str(depth)])
        if branch is not None:
            args.extend(["--branch", branch])

        command = GitCloneCommand(
            git_filepath=self._git_filepath,
            repository=MutableURL(url),
            target_directory=".",
            args=args,
            cwd=str(path),
            envs=envs,
        )
        return self.run(command)

    def fetch_ref_tips(self, url: Union[str, MutableURL], path: Path) -> str:
        """拉取远端所有分支与标签指向的提交，仅下载 commit 与 tag 对象，不下载 tree 与 blob。速度比 clone 更快。

        :param url: 仓库地址
        :param path: 已初始化的 Git 仓库路径
        :return: 返回 fetch 命令执行结果
        """
        # 在执行 Git 操作前校验 URL 安全性，防止历史脏数据绕过
        url_str = str(url)
        try:
            validate_repo_url(url_str)
        except ValueError as e:
            raise GitURLValidationError(str(e))

        # Store branches in "refs/remotes/origin/" as same as cloning, so they can be parsed by `parse_ref`
        refspecs = ["+refs/heads/*:refs/remotes/origin/*", "+refs/tags/*:refs/tags/*"]
        # "--depth=1" skips all ancestor commits, "--filter=tree:0" skips all trees and blobs
        args = ["--depth=1", "--filter=tree:0", "--no-tags"]
        command = GitFetchCommand(
            git_filepath=self._git_filepath,
            repository=MutableURL(url_str),
            refspecs=refspecs,
            args=args,
            cwd=str(path),
        )
        return self.run(command)

    def list_remote(self, url: Union[str, MutableURL]) -> List[Tuple[str, str]]:
        """通过 ls-remote 命令，直接获取远端仓库的 branch 与 tag 等信息。该命令不依赖本地文件系统。

        :param url: 仓库地址
        :return: 命令执行结果，包含 (commit_id, ref) 的列表
        """
        results = []
        for raw_line in self.list_remote_raw(url).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # Known contents which should be skipped
            if line.startswith("warning:"):
                continue

            try:
                commit_id, ref_name = line.split(None)
            except ValueError:
                logger.warning('Failed to parse git branch from ls-remote output, line: "%s"', line)
                continue
            results.append((commit_id, ref_name))
        return results

    def list_remote_raw(self, url: Union[str, MutableURL]) -> str:
        """通过 ls-remote 命令，直接获取远端仓库的 branch 与 tag 等信息。返回命令原始执行结果。

        :param url: 仓库地址
        :return: 命令原始执行结果
        """
        # 在执行 Git 操作前校验 URL 安全性，防止历史脏数据绕过
        url_str = str(url)
        try:
            validate_repo_url(url_str)
        except ValueError as e:
            raise GitURLValidationError(str(e))

        # The "cwd" is pointless for running this command, always use current dir.
        command = GitCommand(
            git_filepath=self._git_filepath, command="ls-remote", end_of_options_args=[url_str], cwd=os.getcwd()
        )
        return self.run(command)

    def list_refs(self, path: Path) -> Generator[Ref, None, None]:
        """获取所有分支和标签。附注标签使用其指向的提交，未指向提交的引用会被忽略。

        :param path: Git 仓库所在的路径。
        """
        # Fields starting with "*" are the object which the annotated tag points to, empty for other refs
        fields = [
            "%(refname)",
            "%(objectname)",
            "%(committerdate:unix)",
            "%(contents)",
            "%(*objectname)",
            "%(*committerdate:unix)",
            "%(*contents)",
        ]
        # Every field ends with NUL, which is not allowed in commit messages by git
        command = GitCommand(
            git_filepath=self._git_filepath,
            command="for-each-ref",
            args=["--format=" + "".join(f"{field}%00" for field in fields)],
            cwd=str(path),
        )
        values = self.run(command).split("\0")
        # The text after the last NUL is the trailing newline, ignore it
        for i in range(0, len(values) - len(fields) + 1, len(fields)):
            ref, commit_id, commit_ts, message, peeled_id, peeled_ts, peeled_message = values[i : i + len(fields)]
            # Each record ends with a newline, and the warnings in stderr(merged into stdout) may be
            # printed before the output, so the ref name is always on the last line.
            ref = ref.rsplit("\n", 1)[-1]
            parsed_obj = self.parse_ref(ref)
            if not parsed_obj:
                continue

            if peeled_ts:
                commit_id, commit_ts, message = peeled_id, peeled_ts, peeled_message
            elif not commit_ts:
                logger.warning("ref %s does not point to a commit, skip it", ref)
                continue

            yield Ref(
                commit_id=commit_id,
                type=parsed_obj[0],
                name=parsed_obj[1],
                commit_time=datetime.fromtimestamp(int(commit_ts)),
                # Keep the trailing newline as the output of "git show --format=%B" used before
                message=message + "\n",
            )

    def clean_meta_info(self, path: Path):
        """清理 git 元信息"""
        shutil.rmtree(path / self.META_GIT_DIR, ignore_errors=True)

    def init_repo(self, path: Path) -> str:
        """初始化 git 仓库"""
        command = GitCommand(git_filepath=self._git_filepath, command="init", args=[], cwd=str(path))
        return self.run(command)

    def add(self, path: Path, *targets: Path) -> str:
        """添加对象到 git 暂存区

        :param path: 工作区目录
        :targets List[path]: 需要添加到暂存区的文件
        """
        args = []
        for target in targets:
            if target.is_absolute():
                args.append(str(target.relative_to(path)))
            else:
                args.append(str(target))

        command = GitCommand(git_filepath=self._git_filepath, command="add", args=args, cwd=str(path))
        return self.run(command)

    def commit(self, path: Path, message: str, envs: Optional[dict] = None) -> str:
        """提交 git 暂存区对象到版本库"""
        command = GitCommand(
            git_filepath=self._git_filepath,
            command="commit",
            args=["-m", message],
            cwd=str(path),
            envs=envs,
        )
        return self.run(command)

    def push(self, path: Path, envs: Optional[dict] = None) -> str:
        """推送 git 提交记录到远程仓库"""
        command = GitCommand(git_filepath=self._git_filepath, command="push", cwd=str(path), envs=envs)
        return self.run(command)

    @staticmethod
    def parse_ref(ref: str) -> Optional[Tuple[str, str]]:
        """解析 ref 字符串，获取分支与标签。

        :return: 包含类型（branch/tag）与值的元组。
        """
        prefixes = [
            ("tag", "refs/tags/"),
            ("branch", "refs/remotes/origin/"),
        ]
        # Ignore HEAD as branch
        invalid_values = {"HEAD"}

        for type_, prefix in prefixes:
            if ref.startswith(prefix):
                value = ref[len(prefix) :]
                if value not in invalid_values:
                    return type_, value
        return None

    def run(self, command: GitCommand, success_code: int = 0) -> str:
        """
        执行 git 命令
        :param GitCommand command: Git 命令封装
        :param int success_code: 期待的执行成功的返回码
        :return: 返回结果
        """
        environment_variables = os.environ.copy()
        environment_variables.update(command.envs or {})
        environment_variables["LANG"] = "en_US.UTF-8"

        with subprocess.Popen(
            command.to_cmd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=environment_variables,
            cwd=command.cwd,
        ) as proc:
            timeout = False
            try:
                stdout, _ = proc.communicate(timeout=self._default_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                timeout = True

            # 不能在 except 中抛异常, 否则 TimeoutExpired 会自动被 traceback 跟踪导致暴露明文的 command 指令
            if timeout:
                raise RequestTimeOutError(
                    f"Command failed: cmd <{command}> execution timeout({self._default_timeout}s)"
                )

            str_stdout = force_str(stdout)
            if proc.returncode != success_code:
                raise self.err_stdout_as_exc(str_stdout, command, proc.returncode)
            return str_stdout

    @staticmethod
    def err_stdout_as_exc(stdout: str, command: GitCommand, return_code: int) -> GitCommandExecutionError:
        """Turn the stdout to an exception object, sensitive texts will be removed.

        :param stdout: The stdout message when running git.
        :param command: The git command object that generated the error.
        :param return_code: The return code of the command.
        """
        # Remove sensitive information form the command
        for text in command.get_sensitive_texts():
            # Use \b to match word boundary only
            stdout = re.sub(rf"\b{text}\b", "", stdout)

        # TODO: Add more logics to remove other sensitive information
        return GitCommandExecutionError(f"Command failed with ({return_code}):\n>>> {command}\n{stdout}")
