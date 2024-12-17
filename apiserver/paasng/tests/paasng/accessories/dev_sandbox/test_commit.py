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

from typing import Dict, List
from unittest import mock

import pytest

from paasng.accessories.dev_sandbox.commit import DevSandboxCodeCommit
from paasng.platform.sourcectl.models import ChangedFile, CommitInfo

pytestmark = pytest.mark.django_db


class StubDevSandboxApiClient:
    def __init__(self, *args, **kwargs): ...

    def fetch_diffs(self) -> List[Dict]:
        return [
            {"path": "webfe/app.js", "action": "added", "content": "js content"},
            {"path": "api/main.py", "action": "modified", "content": "python content"},
            {"path": "backend/cmd/main.go", "action": "deleted", "content": "go content"},
        ]

    def commit(self, commit_msg: str): ...


class StubRepoController:
    def commit_files(self, *args, **kwargs): ...

    def build_url(self, *args, **kwargs) -> str:
        return "https://github.com/octocat/hello-world.git"


class TestDevSandboxCodeCommit:
    @pytest.fixture(autouse=True)
    def _mocks(self):
        with mock.patch(
            "paasng.accessories.dev_sandbox.commit.get_repo_controller",
            return_value=StubRepoController(),
        ), mock.patch(
            "paasng.accessories.dev_sandbox.commit.DevSandboxApiClient",
            new=StubDevSandboxApiClient,
        ):
            yield

    def test_commit(self, bk_user, bk_cnative_app, bk_module, dev_sandbox):
        repo_url = DevSandboxCodeCommit(bk_module, bk_user.username).commit("this is commit message!")
        assert repo_url == "https://github.com/octocat/hello-world.git"

    def test_build_commit_info(self, bk_user, bk_cnative_app, bk_module, dev_sandbox):
        diffs = [
            {"path": "webfe/app.js", "action": "added", "content": "js content"},
            {"path": "api/main.py", "action": "modified", "content": "python content"},
            {"path": "backend/cmd/main.go", "action": "deleted", "content": "go content"},
        ]
        commit_info = DevSandboxCodeCommit(bk_module, bk_user.username)._build_commit_info(
            diffs, "this is commit message!"
        )
        assert commit_info == CommitInfo(
            message="this is commit message!",
            branch="develop",
            add_files=[
                ChangedFile(
                    path="webfe/app.js",
                    content="js content",
                )
            ],
            edit_files=[
                ChangedFile(
                    path="api/main.py",
                    content="python content",
                )
            ],
            delete_files=[
                ChangedFile(
                    path="backend/cmd/main.go",
                    content="go content",
                )
            ],
        )
