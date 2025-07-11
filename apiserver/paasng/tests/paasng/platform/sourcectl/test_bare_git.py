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

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import pytest

from paasng.platform.sourcectl.controllers.bare_git import BareGitRepoController
from paasng.platform.sourcectl.exceptions import ReadLinkFileOutsideDirectoryError
from paasng.platform.sourcectl.git.client import GitCommandExecutionError
from paasng.platform.sourcectl.models import GitRepository, RepoBasicAuthHolder, VersionInfo
from paasng.platform.sourcectl.source_types import get_sourcectl_names
from paasng.platform.sourcectl.utils import generate_temp_dir

pytestmark = pytest.mark.django_db


class TestBareGitRepoController:
    """Test BareGitRepoController"""

    @staticmethod
    def get_fake_repo(bk_module, repo_url):
        r = GitRepository.objects.create(server_name=get_sourcectl_names().bare_git, repo_url=repo_url)
        bk_module.source_type = get_sourcectl_names().bare_git
        bk_module.source_repo_id = r.pk
        bk_module.save(update_fields=["source_type", "source_repo_id"])
        return r

    @staticmethod
    def get_fake_auth_holder(bk_module, repo, username, password):
        return RepoBasicAuthHolder.objects.create(
            username=username,
            password=password,
            repo_id=repo.pk,
            repo_type=get_sourcectl_names().bare_git,
            module=bk_module,
            tenant_id=repo.tenant_id,
        )

    @pytest.mark.parametrize(
        ("auth_token_pair", "repo_url", "target_url"),
        [
            (("admin", "tokenfake"), "http://asdf.com/ddd.git", "http://admin:tokenfake@asdf.com/ddd.git"),
            (("admin", "tokenfake"), "git://asdf.com/ddd.git", "git://admin:tokenfake@asdf.com/ddd.git"),
            (
                ("blues@Smith", "token@fake"),
                "git://asdf.com/ddd.git",
                "git://blues%40Smith:token%40fake@asdf.com/ddd.git",
            ),
        ],
    )
    def test_init_by_module(self, bk_module, auth_token_pair, repo_url, target_url):
        """测试初始化"""
        fake_repo = self.get_fake_repo(bk_module, repo_url)
        self.get_fake_auth_holder(bk_module, fake_repo, auth_token_pair[0], auth_token_pair[1])
        with mock.patch("paasng.platform.sourcectl.models.GitRepository.get_repo_url") as patched_get_repo_url:

            def return_fake_url():
                return repo_url

            patched_get_repo_url.side_effect = return_fake_url

            c = BareGitRepoController.init_by_module(bk_module, "admin")
            assert c.repo_url == target_url

    def test_anonymize_url(self, bk_module):
        with ThreadingHTTPServer(("localhost", 0), BaseHTTPRequestHandler) as httpd:
            threading.Thread(target=httpd.serve_forever).start()
            fake_repo = self.get_fake_repo(bk_module, f"http://localhost:{httpd.server_port}/foo.git")
            self.get_fake_auth_holder(bk_module, fake_repo, "admin", "nopassword")

            c = BareGitRepoController.init_by_module(bk_module, "admin")

            with generate_temp_dir() as working_dir, pytest.raises(GitCommandExecutionError) as exc:
                c.export(
                    working_dir, version_info=VersionInfo(revision="foo", version_type="branch", version_name="master")
                )
            httpd.shutdown()

            value = exc.value
            message = value.args[0]
            assert f"http://localhost:{httpd.server_port}/foo.git" in message
            assert "admin:********" in message
            assert "nopassword" not in message

    @pytest.fixture
    def safe_files_setup(self, tmp_path):
        """Fixture to set up safe files for testing"""
        # Create a normal file
        normal_file = tmp_path / "normal.txt"
        normal_file.write_text("normal content")

        # Create a symbolic link pointing outside the temp directory
        outside_file = tmp_path.parent / "outside.txt"
        outside_file.write_text("sensitive content")

        link_file = tmp_path / "test_link.txt"
        link_file.symlink_to(outside_file)

    @pytest.fixture
    def fake_controller(self, bk_module):
        """Common helper to setup controller with mocked clone operation"""
        fake_repo = self.get_fake_repo(bk_module, "http://localhost/test.git")
        self.get_fake_auth_holder(bk_module, fake_repo, "admin", "password")
        return BareGitRepoController.init_by_module(bk_module, "admin")

    def test_read_files(self, bk_module, fake_controller, safe_files_setup, tmp_path):
        """Test reading a normal file successfully"""
        with (
            mock.patch("paasng.platform.sourcectl.controllers.bare_git.generate_temp_dir") as generate_temp_dir,
            mock.patch.object(fake_controller.client, "clone"),
        ):
            # Patch the generate_temp_dir to return the tmp_path which already been setup
            generate_temp_dir.return_value.__enter__.return_value = tmp_path
            version_info = VersionInfo(revision="test", version_type="branch", version_name="master")

            # Read normal file should succeed
            result = fake_controller.read_file("normal.txt", version_info)
            assert result == b"normal content"

            # Read malicious link file should fail
            with pytest.raises(ReadLinkFileOutsideDirectoryError):
                fake_controller.read_file("test_link.txt", version_info)
