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
from unittest import mock

import pytest
from django.test.utils import override_settings
from django.urls import reverse

from paasng.infras.notifier.client import BkNotificationService
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.connector import get_repo_connector
from paasng.platform.sourcectl.models import SvnAccount
from tests.utils.basic import generate_random_string

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def mocked_call_api():
    with mock.patch.object(BkNotificationService, "send_wecom") as mocked_call:
        mocked_call.return_value = True
        yield mocked_call


@pytest.fixture()
def svn_account(bk_user):
    account, _ = SvnAccount.objects.update_or_create(defaults=dict(account=generate_random_string()), user=bk_user)
    return account


class TestSvnAPI:
    def test_reset_account_error(self, mocked_call_api, api_client, bk_user, svn_account):
        data = {"verification_code": "000000"}
        with override_settings(ENABLE_VERIFICATION_CODE=True):
            response = api_client.put(
                reverse("api.sourcectl.bksvn.accounts.reset", kwargs={"id": svn_account.id}), data
            )

        assert response.status_code == 400
        assert response.json() == {
            "code": "VALIDATION_ERROR",
            "detail": "verification_code: 验证码错误",
            "fields_detail": {"verification_code": ["验证码错误"]},
        }

    def test_reset_account_skip_verification_code(self, mocked_call_api, api_client, bk_user, svn_account):
        with override_settings(ENABLE_VERIFICATION_CODE=False):
            response = api_client.put(reverse("api.sourcectl.bksvn.accounts.reset", kwargs={"id": svn_account.id}), {})

        assert response.status_code == 200


class TestRepoBackendControlViewSet:
    """Test cases for RepoBackendControlViewSet."""

    @pytest.fixture()
    def url(self, bk_app, bk_module):
        return f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/sourcectl/repo/modify/"

    def test_modify_engineless_app_cannot_modify(self, api_client, bk_app, bk_module, url):
        """测试外链应用(无引擎应用)无法修改源码仓库"""
        bk_app.type = "engineless_app"
        bk_app.save()

        data = {
            "source_control_type": "github",
            "source_repo_url": "https://github.com/example/repo.git",
            "source_dir": "",
            "source_repo_auth_info": {},
        }
        response = api_client.post(url, data=data)

        assert response.status_code == 400
        assert response.json()["code"] == "CANNOT_MODIFY_REPO_BACKEND"

    @pytest.mark.parametrize(
        ("repo_url", "auth_info"),
        [
            ("example.com/my-image:latest", {"username": "test", "password": "test123"}),
            ("mirror.tencent.com/my-image:v1.0", {}),
        ],
    )
    def test_modify_image_registry_app(self, api_client, bk_app, bk_module, url, repo_url, auth_info):
        """测试镜像应用修改镜像仓库"""

        bk_module.source_origin = SourceOrigin.IMAGE_REGISTRY
        bk_module.save()

        data = {
            "source_control_type": "",
            "source_repo_url": repo_url,
            "source_repo_auth_info": auth_info,
        }
        response = api_client.post(url, data=data)

        assert response.status_code == 200
        assert repo_url in response.json()["message"]
        assert response.json()["repo_url"] == repo_url

        # 验证数据已更新
        bk_module.refresh_from_db()
        source_obj = bk_module.get_source_obj()
        assert source_obj.get_repo_url() == repo_url

    @pytest.mark.usefixtures("_with_wl_apps")
    def test_modify_source_code_app(self, api_client, bk_app, bk_module, url):
        """测试源码应用修改仓库"""

        bk_module.source_origin = SourceOrigin.AUTHORIZED_VCS
        bk_module.save()

        new_repo_url = "https://github.com/example/new-repo.git"
        data = {
            "source_control_type": "github",
            "source_repo_url": new_repo_url,
            "source_dir": "src",
            "source_repo_auth_info": {},
        }

        # Mock bind 方法以避免实际的仓库连接
        repo_connector = get_repo_connector("github", bk_module)
        with mock.patch.object(type(repo_connector), "bind") as mock_bind:
            response = api_client.post(url, data=data)

        mock_bind.assert_called_once()

        assert response.status_code == 200
        assert new_repo_url in response.json()["message"]
        assert response.json()["repo_url"] == new_repo_url
        assert response.json()["repo_type"] == "github"

    @pytest.mark.usefixtures("_with_wl_apps")
    def test_modify_ai_agent_app_changes_source_origin(self, api_client, bk_app, bk_module, url):
        """测试 AI Agent 应用修改仓库时会更改 source_origin"""

        bk_module.source_origin = SourceOrigin.AI_AGENT
        bk_module.save()

        new_repo_url = "https://github.com/example/ai-agent-repo.git"
        data = {
            "source_control_type": "github",
            "source_repo_url": new_repo_url,
            "source_dir": "",
            "source_repo_auth_info": {},
        }

        # Mock bind 方法
        repo_connector = get_repo_connector("github", bk_module)
        with mock.patch.object(type(repo_connector), "bind") as mock_bind:
            response = api_client.post(url, data=data)

        mock_bind.assert_called_once()
        assert response.status_code == 200
        assert new_repo_url in response.json()["message"]

        # 验证数据已更新
        bk_module.refresh_from_db()
        assert bk_module.source_origin == SourceOrigin.AUTHORIZED_VCS

    def test_cannot_switch_to_bk_svn(self, api_client, bk_app, bk_module, url):
        """测试不能切换到蓝鲸 SVN 仓库"""

        bk_module.source_origin = SourceOrigin.AUTHORIZED_VCS
        bk_module.save()

        data = {
            "source_control_type": "dft_bk_svn",
            "source_repo_url": "svn://example.com/repo",
            "source_dir": "",
            "source_repo_auth_info": {},
        }
        response = api_client.post(url, data=data)

        assert response.status_code == 400
        assert response.json()["code"] == "CANNOT_MODIFY_REPO_BACKEND"
