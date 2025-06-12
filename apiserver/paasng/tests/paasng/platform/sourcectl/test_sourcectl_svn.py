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
import tempfile
from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django_dynamic_fixture import G
from svn.common import SvnException

from paasng.infras.iam.helpers import add_role_members
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.sourcectl.controllers.bk_svn import SvnRepoController
from paasng.platform.sourcectl.models import SvnRepository, VersionInfo
from paasng.platform.sourcectl.serializers import RepositorySLZ
from paasng.platform.sourcectl.source_types import get_sourcectl_names
from paasng.platform.sourcectl.svn.admin import get_svn_authorization_manager
from paasng.platform.sourcectl.svn.client import RepoProvider, SvnRepositoryClient, smart_repo_client
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.platform.templates.templater import TemplateRenderer
from tests.utils import mock

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)
app_code = "ng-unittest-app"


class TestRepoProvider:
    @mock.patch("paasng.platform.sourcectl.svn.client.LocalClient")
    @mock.patch("paasng.platform.sourcectl.svn.client.RemoteClient")
    def test_provision(self, rclient, lclient, bk_app):
        provider = RepoProvider(
            base_url="svn://svn.bking.com:80/apps/ngdemo/trunk/__apps/", username="svn", password=""
        )
        # Mock Remote and Local Instance
        rclient = rclient.return_value

        rclient.list.return_value = []
        result = provider.provision(desired_name=bk_app.code)
        assert result["already_initialized"] is True

        rclient.list.side_effect = SvnException("svn: E200009")
        result = provider.provision(desired_name=bk_app.code)
        assert result["already_initialized"] is False

        rclient.list.side_effect = SvnException("svn: Exxxxxx")
        with pytest.raises(SvnException):
            provider.provision(desired_name=bk_app.code)


class TestSvnRepositoryClientV2:
    @pytest.mark.usefixtures("_init_tmpls")
    @mock.patch("paasng.platform.sourcectl.svn.client.LocalClient")
    @mock.patch("paasng.platform.sourcectl.svn.client.RemoteClient")
    def test_download_template_from_svn(self, rclient, lclient, bk_app, bk_user):
        client = SvnRepositoryClient(repo_url="svn://faked-repo", username="fake_username", password="fake_password")
        # Mock Remote and Local Instance
        context = {
            "region": settings.DEFAULT_REGION_NAME,
            "owner_username": bk_user.username,
            "app_code": bk_app.code,
            "app_secret": "fake-secret-created-by-unittests",
            "app_name": bk_app.name,
        }
        with generate_temp_dir() as working_dir:
            TemplateRenderer(
                settings.DUMMY_TEMPLATE_NAME,
                context,
            ).write_to_dir(working_dir)

            client.sync_dir(local_path=working_dir, remote_path="trunk")
        rclient().list.assert_called()
        rclient().checkout.assert_called()
        # lclient().add.assert_called()
        lclient().commit.assert_called()

    @pytest.fixture()
    def svn_client(self, svn_repo_credentials):
        return smart_repo_client(**svn_repo_credentials)

    def test_export_normal(self, svn_client):
        with generate_temp_dir() as working_dir:
            svn_client.export("", working_dir)
            assert len(os.listdir(working_dir)) > 1

    def test_get_latest_revison(self, svn_client):
        svn_client.get_latest_revision()

    def test_package(self, svn_client):
        file_path = tempfile.mktemp(suffix=".tar.gz")
        svn_client.package("", file_path)
        assert os.path.exists(file_path)

    def test_list_alternative_versions(self, svn_client):
        results = svn_client.list_alternative_versions()
        assert results
        # "trunk" should always be the first item
        assert results[0].name == "trunk"

    def test_extract_smart_revision(self, svn_client):
        with pytest.raises(ValueError, match=r".* is not a valid smart revision.*"):
            svn_client.extract_smart_revision("invalid")

        assert svn_client.extract_smart_revision("trunk:trunk") is not None


class TestRepositorySLZ:
    def test_create_repo(self):
        svn_repo = G(
            SvnRepository,
            server_name=get_sourcectl_names().bk_svn,
            repo_url="svn://svn-server/dirname",
            region=settings.DEFAULT_REGION_NAME,
        )
        svn_repo.trunk_url = svn_repo.get_trunk_url()
        serializer = RepositorySLZ(svn_repo)

        assert serializer.data["trunk_url"] == "svn://svn-server/dirname/trunk"


@mock.patch("paasng.platform.sourcectl.svn.admin.IeodSvnAuthClient.request")
class TestSvnAuth:
    def test_create_app(self, auth_client_request, bk_app):
        def side_effect(url, params, **kwargs):
            return params

        auth_client_request.side_effect = side_effect

        mock_mod_authz = Mock(return_value={})
        authorization_manager = get_svn_authorization_manager(bk_app)
        with patch.object(authorization_manager.svn_client, "mod_authz", mock_mod_authz):
            path = f"{bk_app.code}-123"
            authorization_manager.initialize(path)

            assert mock_mod_authz.called
            args, kwargs = mock_mod_authz.call_args_list[0]
            assert kwargs["repo_path"].endswith(f"/{bk_app.code}-123")

    @pytest.mark.parametrize(
        ("username", "role", "added"),
        [
            ("bar", ApplicationRole.DEVELOPER, True),
            ("baz", ApplicationRole.ADMINISTRATOR, True),
        ],
    )
    def test_update_developers(self, auth_client_request, bk_app, bk_user, username, role, added):
        def side_effect(url, params, **kwargs):
            return params

        auth_client_request.side_effect = side_effect

        mock_add_group = Mock(return_value={})
        authorization_manager = get_svn_authorization_manager(bk_app)
        with patch.object(authorization_manager.svn_client, "add_group", mock_add_group):
            add_role_members(bk_app.code, role, username)
            authorization_manager.update_developers()

            assert mock_add_group.called
            args, kwargs = mock_add_group.call_args_list[0]
            assert args[0] == bk_app.code
            if added:
                assert set(kwargs["developers"].split(";")) == {bk_user.username, username}
            else:
                assert set(kwargs["developers"].split(";")) == {bk_user.username}


class TestRepoSvnController:
    @pytest.fixture()
    def controller(self):
        repo_url = "svn://faked-svn/apps/foo-app"
        credentials = {"username": "", "password": ""}
        controller = SvnRepoController(repo_url, credentials)
        return controller

    def test_build_url_trunk(self, controller):
        version = VersionInfo("1", "trunk", "trunk")
        assert controller.build_url(version) == "svn://faked-svn/apps/foo-app/trunk"

    def test_build_url_branch(self, controller):
        version = VersionInfo("1", "v1", "branches")
        assert controller.build_url(version) == "svn://faked-svn/apps/foo-app/branches/v1"

    def test_build_url_tag(self, controller):
        version = VersionInfo("1", "v1", "tags")
        assert controller.build_url(version) == "svn://faked-svn/apps/foo-app/tags/v1"
