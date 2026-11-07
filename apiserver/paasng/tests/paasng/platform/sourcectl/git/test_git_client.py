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

import datetime
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
from blue_krill.data_types.url import MutableURL

from paasng.platform.sourcectl.git.client import (
    GitClient,
    GitCloneCommand,
    GitCommand,
    GitFetchCommand,
    GitURLValidationError,
)


class TestGitCommand:
    """测试 GitCommand 参数隔离机制"""

    def test_to_cmd_without_end_of_options_args(self):
        """无 end-of-options 参数时不应插入 --"""
        command = GitCommand(git_filepath="git", command="show-ref")
        assert command.to_cmd() == ["git", "show-ref"]

    def test_to_cmd_with_options_only(self):
        """仅有选项参数时不应插入 --"""
        command = GitCommand(git_filepath="git", command="show", args=["-s", "--format=%ct/%B"])
        assert command.to_cmd() == ["git", "show", "-s", "--format=%ct/%B"]

    def test_to_cmd_with_end_of_options_args(self):
        """有 end-of-options 参数时应自动插入 --"""
        command = GitCommand(
            git_filepath="git", command="ls-remote", end_of_options_args=["http://example.com/repo.git"]
        )
        assert command.to_cmd() == ["git", "ls-remote", "--", "http://example.com/repo.git"]

    def test_to_cmd_with_mixed_args(self):
        """选项参数在 -- 之前，end-of-options 参数在 -- 之后"""
        command = GitCommand(git_filepath="git", command="checkout", args=["-b"], end_of_options_args=["new-branch"])
        assert command.to_cmd() == ["git", "checkout", "-b", "--", "new-branch"]


class TestGitCloneCommand:
    @pytest.fixture()
    def command(self):
        return GitCloneCommand(
            git_filepath="/path/to/git",
            repository=MutableURL("http://username:password@hostname"),
            args=["--bar", "baz"],
            cwd=".",
        )

    def test_to_command(self, command):
        """clone 命令应在选项和仓库 URL 之间插入 --"""
        assert command.to_cmd() == [
            "/path/to/git",
            "clone",
            "--bar",
            "baz",
            "--",
            "http://username:password@hostname",
            ".",
        ]

    def test_to_obscure_cmd(self, command):
        assert command.to_cmd(obscure=True) == [
            "/path/to/git",
            "clone",
            "--bar",
            "baz",
            "--",
            "http://username:********@hostname",
            ".",
        ]


class TestGitFetchCommand:
    @pytest.fixture()
    def command(self):
        return GitFetchCommand(
            git_filepath="/path/to/git",
            repository=MutableURL("http://username:password@hostname"),
            refspecs=["+refs/heads/*:refs/remotes/origin/*"],
            args=["--depth=1"],
            cwd=".",
        )

    def test_to_obscure_cmd(self, command):
        assert command.to_cmd(obscure=True) == [
            "/path/to/git",
            "fetch",
            "--depth=1",
            "--",
            "http://username:********@hostname",
            "+refs/heads/*:refs/remotes/origin/*",
        ]


class TestGitClient:
    @pytest.fixture()
    def client(self):
        return GitClient()

    def test_checkout(self, client):
        """checkout 的分支名应位于 -- 之后"""
        with patch.object(client, "run") as mock_run:
            client.checkout(Path("."), "master")
            command = mock_run.call_args[0][0]
            assert isinstance(command, GitCommand)
            assert command.to_cmd() == ["git", "checkout", "--", "master"]

    def test_clone(self, client):
        """clone 的仓库 URL 和目标目录应位于 -- 之后"""
        with patch.object(client, "run") as mock_run:
            client.clone("http://username:password@hostname", Path("."))
            command = mock_run.call_args[0][0]

            assert isinstance(command, GitCloneCommand)
            assert command.to_cmd() == ["git", "clone", "--", "http://username:password@hostname", "."]

    def test_fetch_ref_tips(self, client):
        """只拉取分支与标签指向的提交，仓库 URL 位于 -- 之后"""
        with patch.object(client, "run") as mock_run:
            client.fetch_ref_tips("http://username:password@hostname/foo.git", Path("fake_dir"))
            command = mock_run.call_args[0][0]

            assert isinstance(command, GitFetchCommand)
            assert command.cwd == "fake_dir"
            assert command.to_cmd() == [
                "git",
                "fetch",
                "--depth=1",
                "--filter=tree:0",
                "--no-tags",
                "--",
                "http://username:password@hostname/foo.git",
                "+refs/heads/*:refs/remotes/origin/*",
                "+refs/tags/*:refs/tags/*",
            ]

    def test_fetch_ref_tips_rejects_dash_url(self, client):
        """以 - 开头的 URL 应被 URL 校验拒绝"""
        with pytest.raises(GitURLValidationError):
            client.fetch_ref_tips("-c core.sshCommand=evil", Path("fake_dir"))

    def test_list_refs(self, client):
        """测试通过 for-each-ref 一次读取所有分支和标签"""
        records = [
            # (refname, objectname, committerdate, contents, *objectname, *committerdate, *contents)
            ("refs/remotes/origin/master", "c1", "1583313687", "add foo\n", "", "", ""),
            ("refs/remotes/origin/HEAD", "c1", "1583313687", "add foo\n", "", "", ""),
            ("refs/remotes/origin/develop/1.2", "c2", "1583313688", "asdf \n 中文./,';[]\n\t", "", "", ""),
            ("refs/heads/develop", "c2", "1583313688", "asdf", "", "", ""),
            ("refs/stash", "c2", "1583313688", "asdf", "", "", ""),
            # lightweight tag
            ("refs/tags/v1", "c1", "1583313687", "add foo\n", "", "", ""),
            # annotated tag, use the commit it points to
            ("refs/tags/v2", "t2", "", "tag message\n", "c2", "1583313688", "asdf"),
            # tag points to a tree, skip it
            ("refs/tags/tree-tag", "t3", "", "tag message\n", "tree3", "", ""),
        ]
        output = "".join("".join(f"{field}\0" for field in record) + "\n" for record in records)

        with patch.object(client, "run") as mock_run:
            # stderr is merged into stdout, the output may begin with warnings
            mock_run.return_value = "warning: some warning\n" + output
            refs = list(client.list_refs(Path("fake_dir")))

            command = mock_run.call_args[0][0]
            assert isinstance(command, GitCommand)
            assert command.to_cmd()[:2] == ["git", "for-each-ref"]

        assert [(ref.type, ref.name, ref.commit_id, ref.message) for ref in refs] == [
            ("branch", "master", "c1", "add foo\n\n"),
            ("branch", "develop/1.2", "c2", "asdf \n 中文./,';[]\n\t\n"),
            ("tag", "v1", "c1", "add foo\n\n"),
            ("tag", "v2", "c2", "asdf\n"),
        ]
        assert refs[0].commit_time == datetime.datetime.fromtimestamp(1583313687)
        assert refs[3].commit_time == datetime.datetime.fromtimestamp(1583313688)

    @pytest.mark.parametrize(
        ("cmd_result", "expected"),
        [
            (
                "0123456789   HEAD\n0123456789 refs/heads/master",
                [
                    ("0123456789", "HEAD"),
                    ("0123456789", "refs/heads/master"),
                ],
            ),
        ],
    )
    def test_list_remote(self, client, cmd_result, expected):
        with patch.object(client, "run") as mock_run:
            mock_run.return_value = cmd_result
            assert client.list_remote("http://example.com/foo.git") == expected

    def test_list_remote_command_has_separator(self, client):
        """ls-remote 的 URL 应位于 -- 之后"""
        with patch.object(client, "run") as mock_run:
            mock_run.return_value = ""
            client.list_remote("http://example.com/foo.git")
            command = mock_run.call_args[0][0]
            assert isinstance(command, GitCommand)
            assert command.to_cmd() == ["git", "ls-remote", "--", "http://example.com/foo.git"]

    def test_list_remote_rejects_dash_url(self, client):
        """以 - 开头的 URL 应被 URL 校验拒绝"""
        with pytest.raises(GitURLValidationError):
            client.list_remote("-c core.sshCommand=evil")

    def test_list_remote_with_warning_and_invalid(self, client):
        # The command output a warning message sometimes
        with patch.object(client, "run") as mock_run:
            mock_run.return_value = dedent(
                """\
                warning: redirecting to http://example.com/foo.git/
                0123456789   HEAD
                <some random invalid output>
"""
            )
            assert client.list_remote("http://example.com/foo.git") == [("0123456789", "HEAD")]

    def test_err_stdout_as_exc(self, client):
        """Test the sensitive information is scrubbed."""
        # Use a password contains escaped special characters, orig user/pass: foo/pass@%wd
        command = GitCloneCommand("git", repository=MutableURL("https://foo:pass%40%25wd@example.com/foo.git"))
        stdout = dedent(
            """\
            Cloning into '.'...
            fatal: Authentication failed for 'https://foo:pass%40%25wd@example.com/foo.git'
        """
        )
        exc = client.err_stdout_as_exc(stdout, command, -1)
        assert "foo:pass%40%25wd" not in str(exc), "The sensitive information should be scrubbed."
        assert "failed for 'https://example.com/foo.git'" in str(exc)
