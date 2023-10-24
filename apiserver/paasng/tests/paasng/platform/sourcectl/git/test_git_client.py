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
import datetime
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import pytest
from blue_krill.data_types.url import MutableURL

from paasng.platform.sourcectl.git.client import GitClient, GitCloneCommand, GitCommand


class TestGitCloneCommand:
    @pytest.fixture
    def command(self):
        return GitCloneCommand(
            git_filepath="/path/to/git",
            repository=MutableURL("http://username:password@hostname"),
            args=["--bar", "baz"],
            cwd=".",
        )

    def test_to_command(self, command):
        assert command.to_cmd() == [
            "/path/to/git",
            "clone",
            "--bar",
            "baz",
            "http://username:password@hostname",
            ".",
        ]

    def test_to_obscure_cmd(self, command):
        assert command.to_cmd(obscure=True) == [
            "/path/to/git",
            "clone",
            "--bar",
            "baz",
            "http://username:********@hostname",
            ".",
        ]


class TestGitClient:
    @pytest.fixture
    def client(self):
        return GitClient()

    def test_checkout(self, client):
        with patch.object(client, "run") as mock_run:
            client.checkout(Path("."), "master")
            command = mock_run.call_args[0][0]
            assert isinstance(command, GitCommand)
            assert command.to_cmd() == ["git", "checkout", "master"]

    @pytest.mark.parametrize(
        "expected",
        [
            ['git', 'clone', 'http://username:password@hostname', '.'],
        ],
    )
    def test_clone(self, client, expected):
        with patch.object(client, "run") as mock_run:
            client.clone("http://username:password@hostname", Path("."))
            command = mock_run.call_args[0][0]

            assert isinstance(command, GitCloneCommand)
            assert command.to_cmd() == expected

    @pytest.mark.parametrize(
        "refs,expected",
        [
            (["9n8b7u6y5t refs/remotes/origin/master", "9n8b7u6y5t refs/heads/HEAD"], {"branch": ["master"]}),
            (
                [
                    "9n8b7u6y5t refs/stash",
                    "9n8b7u6y5t refs/heads/develop",
                    "9n8b7u6y5t refs/remotes/origin/develop",
                    "9n8b7u6y5t refs/tags/develop",
                    "9n8b7u6y5t refs/tags/v20210203",
                ],
                {"branch": ["develop"], "tag": ["develop", "v20210203"]},
            ),
            (["9n8b7u6y5t refs/remotes/origin/develop/1.2"], {"branch": ["develop/1.2"]}),
        ],
    )
    def test_list_refs(self, client, refs, expected):
        """测试 git show-ref"""

        with patch.object(client, "run") as mock_run, patch(
            "paasng.platform.sourcectl.git.client.GitClient._get_commit_info"
        ) as mock_commit_info:
            mock_run.return_value = "\n".join(refs)
            mock_commit_info.return_value = {"time": "2019-01-01 00:00:00", "message": "fake"}

            result = defaultdict(list)
            for x in client.list_refs(Path("fake_dir")):
                result[x.type].append(x.name)

            assert result == expected
            command = mock_run.call_args[0][0]
            assert isinstance(command, GitCommand)
            assert command.to_cmd() == ["git", "show-ref"]

    @pytest.mark.parametrize(
        "cmd_result,expected",
        [
            (
                "0123456789   HEAD\n0123456789 refs/heads/master",
                [
                    ('0123456789', 'HEAD'),
                    ('0123456789', 'refs/heads/master'),
                ],
            ),
        ],
    )
    def test_list_remote(self, client, cmd_result, expected):
        with patch.object(client, "run") as mock_run:
            mock_run.return_value = cmd_result
            assert client.list_remote(Path("fake_dir")) == expected

    @pytest.mark.parametrize(
        "commits,expected",
        [
            (
                ["1583313687/add asdfas fasdfa"],
                {"time": datetime.datetime.fromtimestamp(1583313687), "message": "add asdfas fasdfa"},
            ),
            (
                ["1583313687/asdf \n 中文./,';[]\n\t"],
                {"time": datetime.datetime.fromtimestamp(1583313687), "message": "asdf \n 中文./,';[]\n\t"},
            ),
        ],
    )
    def test_get_commit_info(self, client, commits, expected):
        """测试 git show"""
        with patch.object(client, "run") as mock_run:
            mock_run.return_value = "\n".join(commits)

            assert client._get_commit_info(Path("fake_dir"), "9n8b7u6y5t") == expected
            command = mock_run.call_args[0][0]

            assert isinstance(command, GitCommand)
            assert command.to_cmd() == ["git", "show", "-s", "--format=%ct/%B", "9n8b7u6y5t"]
