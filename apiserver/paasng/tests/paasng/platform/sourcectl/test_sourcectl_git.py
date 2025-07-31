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

import datetime
import logging
import os

import pytest
from dateutil.tz.tz import tzoffset, tzutc

from paasng.platform.sourcectl.controllers.gitee import GiteeRepoController
from paasng.platform.sourcectl.controllers.github import GitHubRepoController
from paasng.platform.sourcectl.controllers.gitlab import GitlabRepoController
from paasng.platform.sourcectl.models import AlternativeVersion, VersionInfo
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir, generate_temp_file
from tests.utils import mock

pytestmark = pytest.mark.django_db
logger = logging.getLogger(__name__)


@pytest.fixture()
def mock_gitlab_client():
    with mock.patch("paasng.platform.sourcectl.controllers.gitlab.GitLabApiClient") as client_clz:
        yield client_clz()


class TestGitlabRepoController:
    @pytest.fixture()
    def version(self):
        return VersionInfo("revision", "master", "branch")

    @pytest.fixture()
    def tarball_bytes(self):
        with generate_temp_dir() as tmp_dir, generate_temp_file(suffix=".tar.gz") as tmp_file:
            (tmp_dir / "foo").mkdir(0o755, parents=True, exist_ok=True)
            for filename in ["foo/readme.md", "foo/some-py.py"]:
                (tmp_dir / filename).write_text(filename)
            compress_directory(tmp_dir, tmp_file)
            yield tmp_file.read_bytes()

    def test_export_normal(self, gitlab_repo_url, mock_gitlab_client, version, tarball_bytes):
        def mock_repo_archive(project, local_path, ref):
            with open(local_path, "wb") as fh:
                fh.write(tarball_bytes)

        mock_gitlab_client.repo_archive.side_effect = mock_repo_archive
        controller = GitlabRepoController(repo_url=gitlab_repo_url, user_credentials={}, api_url="")
        with generate_temp_dir() as working_dir:
            controller.export(working_dir, version)
            assert mock_gitlab_client.repo_archive.called
            assert len(os.listdir(working_dir)) > 1

    def test_get_owner_and_repo(self, mock_gitlab_client, gitlab_repo_url):
        controller = GitlabRepoController(repo_url=gitlab_repo_url, user_credentials={}, api_url="")
        assert controller.project.namespace == "owner"
        assert controller.project.name == "repo"

    def test_list_alternative_versions(self, mock_gitlab_client, gitlab_repo_url):
        # Use UTC time
        fake_date_1 = datetime.datetime(2018, 12, 14, 9, 13, 47, 0, tzinfo=tzutc())
        fake_date_2 = datetime.datetime(2018, 12, 14, 9, 13, 48, 0, tzinfo=tzutc())
        fake_date_3 = datetime.datetime(2018, 12, 14, 9, 13, 49, 0, tzinfo=tzutc())
        fake_date_4 = datetime.datetime(2018, 12, 14, 9, 13, 50, 0, tzinfo=tzutc())
        fake_branch_list = [
            {
                "name": "master",
                "commit": {
                    "id": "fake_hash_id",
                    "committed_date": "2018-12-14T17:13:47.000000+08:00",
                    "message": "branch-1",
                },
            },
            {
                "name": "staging",
                "commit": {
                    "id": "fake_hash_id",
                    "committed_date": "2018-12-14T17:13:48.000000+08:00",
                    "message": "branch-2",
                },
            },
        ]
        fake_tag_list = [
            {
                "name": "v1",
                "commit": {
                    "id": "fake_hash_id",
                    "committed_date": "2018-12-14T17:13:49.000000+08:00",
                    "message": "v1",
                },
            },
            {
                "name": "v2",
                "commit": {"id": "fake_hash_id", "committed_date": "2018-12-14T17:13:50.000000+08:00"},
                "message": "v2",
            },
        ]
        # 分支展示，从新到旧
        fake_list_alternative_versions = [
            AlternativeVersion("v2", "tag", "fake_hash_id", gitlab_repo_url, fake_date_4, "v2"),
            AlternativeVersion("v1", "tag", "fake_hash_id", gitlab_repo_url, fake_date_3, "v1"),
            AlternativeVersion("staging", "branch", "fake_hash_id", gitlab_repo_url, fake_date_2, "branch-2"),
            AlternativeVersion("master", "branch", "fake_hash_id", gitlab_repo_url, fake_date_1, "branch-1"),
        ]

        def mock_repo_list_branches(*args, **kwargs):
            return fake_branch_list

        def mock_repo_list_tags(*args, **kwargs):
            return fake_tag_list

        mock_gitlab_client.repo_list_branches = mock_repo_list_branches
        mock_gitlab_client.repo_list_tags = mock_repo_list_tags
        controller = GitlabRepoController(repo_url=gitlab_repo_url, user_credentials={}, api_url="")
        assert controller.list_alternative_versions() == fake_list_alternative_versions

    def test_extract_version_info(self, mock_gitlab_client, gitlab_repo_url, version):
        controller = GitlabRepoController(repo_url=gitlab_repo_url, user_credentials={}, api_url="")
        assert controller.extract_version_info(version) == ("master", "revision")

    @pytest.mark.parametrize(
        ("smart_revision", "expected"),
        [
            ("revision", "revision"),
            ("branch:master", "fake-master-id"),
            ("tag:foo", "bar"),
        ],
    )
    def test_extract_smart_revision(self, mock_gitlab_client, gitlab_repo_url, smart_revision, expected):
        def mock_repo_last_commit(project, branch_or_hash):
            if branch_or_hash == "master":
                return {"id": "fake-master-id"}
            elif branch_or_hash == "foo":
                return {"id": "bar"}
            return {}

        mock_gitlab_client.repo_last_commit.side_effect = mock_repo_last_commit
        controller = GitlabRepoController(repo_url=gitlab_repo_url, user_credentials={}, api_url="")
        assert controller.extract_smart_revision(smart_revision) == expected

    def test_build_url(self, mock_gitlab_client, gitlab_repo_url, version):
        controller = GitlabRepoController(repo_url=gitlab_repo_url, user_credentials={}, api_url="")
        assert controller.build_url(version) == gitlab_repo_url


class TestGithubRepoController:
    @pytest.fixture()
    def version(self):
        return VersionInfo("revision", "master", "branch")

    @pytest.fixture()
    def user_credentials(self):
        return {"oauth_token": "this is a github access token"}

    def test_get_project(self, user_credentials, github_repo_url):
        controller = GitHubRepoController("", github_repo_url, user_credentials)
        assert controller.project.namespace == "owner"
        assert controller.project.name == "repo"

    @pytest.fixture()
    def client(self):
        with mock.patch("paasng.platform.sourcectl.controllers.github.GitHubApiClient") as client_clz:
            yield client_clz()

    def test_list_all_repositories(self, client, github_repo_url, user_credentials):
        def mock_list_repo(*args, **kwargs):
            return [
                {
                    "owner": {
                        "login": "octocat",
                        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
                    },
                    "name": "Hello-World",
                    "description": "This your first repo!",
                    "html_url": "https://github.com/octocat/Hello-World",
                    "clone_url": "https://github.com/octocat/Hello-World.git",
                    "ssh_url": "git@github.com:octocat/Hello-World.git",
                    "created_at": "2011-01-26T19:01:12Z",
                    "updated_at": "2011-01-26T19:14:43Z",
                },
                {
                    "owner": {
                        "login": "octocat",
                        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
                    },
                    "name": "hello-worId",
                    "description": "My first repository on GitHub.",
                    "html_url": "https://github.com/octocat/hello-worId",
                    "clone_url": "https://github.com/octocat/hello-worId.git",
                    "ssh_url": "git@github.com:octocat/hello-worId.git",
                    "created_at": "2014-01-26T19:01:12Z",
                    "updated_at": "2014-01-26T19:14:43Z",
                },
            ]

        client.list_repo.side_effect = mock_list_repo
        ret = GitHubRepoController.list_all_repositories(api_url=github_repo_url, user_credentials=user_credentials)
        assert len(ret) == 2
        assert ret[0].namespace == "octocat"
        assert ret[0].project == "Hello-World"
        assert ret[0].description == "This your first repo!"
        assert ret[0].last_activity_at == datetime.datetime(2011, 1, 26, 19, 14, 43, tzinfo=tzutc())
        assert ret[1].web_url == "https://github.com/octocat/hello-worId"
        assert ret[1].http_url_to_repo == "https://github.com/octocat/hello-worId.git"
        assert ret[1].ssh_url_to_repo == "git@github.com:octocat/hello-worId.git"
        assert ret[1].created_at == datetime.datetime(2014, 1, 26, 19, 1, 12, tzinfo=tzutc())

    def test_list_alternative_versions(self, client, github_repo_url, user_credentials):
        fake_branch_list = [
            {
                "name": "master",
                "commit": {"sha": "fake_hash_id_0", "url": "fake_url_0"},
            },
            {
                "name": "develop",
                "commit": {"sha": "fake_hash_id_1", "url": "fake_url_1"},
            },
        ]
        fake_tag_list = [
            {
                "name": "v1",
                "commit": {"sha": "fake_hash_id_2", "url": "fake_url_2"},
            },
            {
                "name": "v2",
                "commit": {"sha": "fake_hash_id_3", "url": "fake_url_3"},
                "message": "v2",
            },
        ]

        def mock_repo_list_branches(*args, **kwargs):
            return fake_branch_list

        def mock_repo_list_tags(*args, **kwargs):
            return fake_tag_list

        client.repo_list_branches = mock_repo_list_branches
        client.repo_list_tags = mock_repo_list_tags
        controller = GitHubRepoController("", github_repo_url, user_credentials)
        versions = controller.list_alternative_versions()
        assert versions[0].name == "master"
        assert versions[0].revision == "fake_hash_id_0"
        assert versions[1].type == "branch"
        assert versions[2].revision == "fake_hash_id_2"
        assert versions[3].type == "tag"

    def test_extract_smart_revision(self, client, github_repo_url, user_credentials):
        def mock_repo_last_commit(*args, **kwargs):
            return {"sha": "fake_hash_id"}

        client.repo_last_commit.side_effect = mock_repo_last_commit
        controller = GitHubRepoController("", github_repo_url, user_credentials)
        assert controller.extract_smart_revision("branch:master") == "fake_hash_id"

    def test_build_url(self, github_repo_url, user_credentials, version):
        controller = GitHubRepoController("", github_repo_url, user_credentials)
        assert controller.build_url(version) == github_repo_url

    def test_read_file(self, client, github_repo_url, user_credentials, version):
        def mock_repo_get_raw_file(*args, **kwargs) -> bytes:
            return b"file content..."

        client.repo_get_raw_file.side_effect = mock_repo_get_raw_file
        controller = GitHubRepoController("", github_repo_url, user_credentials)
        assert controller.read_file("/fake_path", version) == b"file content..."


class TestGiteebRepoController:
    @pytest.fixture()
    def version(self):
        return VersionInfo("revision", "master", "branch")

    @pytest.fixture()
    def user_credentials(self):
        return {"oauth_token": "this is a gitee access token"}

    def test_get_project(self, user_credentials, gitee_repo_url):
        controller = GiteeRepoController("", gitee_repo_url, user_credentials)
        assert controller.project.namespace == "owner"
        assert controller.project.name == "repo"

    @pytest.fixture()
    def client(self):
        with mock.patch("paasng.platform.sourcectl.controllers.gitee.GiteeApiClient") as client_clz:
            yield client_clz()

    def test_list_all_repositories(self, client, gitee_repo_url, user_credentials):
        def mock_list_repo(*args, **kwargs):
            return [
                {
                    "namespace": {
                        "path": "octocat",
                    },
                    "owner": {
                        "login": "octocat",
                        "avatar_url": "https://gitee.com/assets/no_portrait.png",
                    },
                    "name": "Hello-World",
                    "description": "My first repository on Gitee.",
                    "html_url": "https://gitee.com/octocat/helloworld",
                    "ssh_url": "git@gitee.com:octocat/helloworld.git",
                    "created_at": "2022-05-24T11:07:30+08:00",
                    "updated_at": "2022-05-24T11:07:33+08:00",
                },
            ]

        client.list_repo.side_effect = mock_list_repo
        ret = GiteeRepoController.list_all_repositories(api_url=gitee_repo_url, user_credentials=user_credentials)
        assert len(ret) == 1
        assert ret[0].namespace == "octocat"
        assert ret[0].project == "Hello-World"
        assert ret[0].description == "My first repository on Gitee."
        assert ret[0].last_activity_at == datetime.datetime(2022, 5, 24, 11, 7, 33, tzinfo=tzoffset(None, 28800))

    def test_list_alternative_versions(self, client, gitee_repo_url, user_credentials):
        fake_branch_list = [
            {
                "name": "master",
                "commit": {"sha": "fake_hash_id_0", "url": "fake_url_0"},
            },
            {
                "name": "develop",
                "commit": {"sha": "fake_hash_id_1", "url": "fake_url_1"},
            },
        ]
        fake_tag_list = [
            {
                "name": "v1",
                "commit": {"sha": "fake_hash_id_2", "url": "fake_url_2"},
            },
            {
                "name": "v2",
                "commit": {"sha": "fake_hash_id_3", "url": "fake_url_3"},
                "message": "v2",
            },
        ]

        def mock_repo_list_branches(*args, **kwargs):
            return fake_branch_list

        def mock_repo_list_tags(*args, **kwargs):
            return fake_tag_list

        client.repo_list_branches = mock_repo_list_branches
        client.repo_list_tags = mock_repo_list_tags
        controller = GiteeRepoController("", gitee_repo_url, user_credentials)
        versions = controller.list_alternative_versions()
        assert versions[0].name == "master"
        assert versions[0].revision == "fake_hash_id_0"
        assert versions[1].type == "branch"
        assert versions[2].revision == "fake_hash_id_2"
        assert versions[3].type == "tag"

    def test_extract_smart_revision(self, client, gitee_repo_url, user_credentials):
        def mock_repo_last_commit(*args, **kwargs):
            return {"sha": "fake_hash_id"}

        client.repo_last_commit.side_effect = mock_repo_last_commit
        controller = GiteeRepoController("", gitee_repo_url, user_credentials)
        assert controller.extract_smart_revision("branch:master") == "fake_hash_id"

    def test_build_url(self, gitee_repo_url, user_credentials, version):
        controller = GiteeRepoController("", gitee_repo_url, user_credentials)
        assert controller.build_url(version) == gitee_repo_url

    def test_read_file(self, client, gitee_repo_url, user_credentials, version):
        def mock_repo_get_raw_file(*args, **kwargs) -> bytes:
            return b"file content..."

        client.repo_get_raw_file.side_effect = mock_repo_get_raw_file
        controller = GiteeRepoController("", gitee_repo_url, user_credentials)
        assert controller.read_file("/fake_path", version) == b"file content..."


class TestControllerUtils:
    @pytest.fixture()
    def branch_data(self):
        return {
            "name": "translation",
            "commit": {
                "id": "da8e366ca6ed81e987410b97472fb827c4335ff4",
                "message": "msg",
                "committed_date": "2018-07-25T19:46:51.000+08:00",
            },
        }

    @pytest.fixture()
    def controller(self, gitlab_repo_url):
        with mock.patch("paasng.platform.sourcectl.controllers.gitlab.GitLabApiClient"):
            yield GitlabRepoController(repo_url=gitlab_repo_url, user_credentials={}, api_url="")

    def test_branch_data_to_version_normal(self, branch_data, controller):
        ver = controller._branch_data_to_version("branch", branch_data)
        assert isinstance(ver.last_update, datetime.datetime)

    def test_branch_data_to_version_other_timezone(self, branch_data, controller):
        data = {**branch_data, "committed_date": "2018-07-25T19:46:51.000-07:00"}
        ver = controller._branch_data_to_version("branch", data)
        assert isinstance(ver.last_update, datetime.datetime)
