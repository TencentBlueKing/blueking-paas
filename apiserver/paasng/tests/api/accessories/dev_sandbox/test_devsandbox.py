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

from typing import List
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status

from paas_wl.bk_app.dev_sandbox.conf import DEV_SANDBOX_WORKSPACE
from paas_wl.bk_app.dev_sandbox.constants import DevSandboxStatus
from paas_wl.bk_app.dev_sandbox.controller import DevSandboxDetail, DevSandboxUrls
from paasng.platform.sourcectl.models import AlternativeVersion

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestListDevSandbox:
    """获取开发沙箱列表"""

    def test_list(self, api_client, bk_cnative_app, bk_dev_sandbox):
        resp = api_client.get(reverse("accessories.dev_sandbox.list_create", kwargs={"code": bk_cnative_app.code}))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) >= 1

        dev_sandbox = [sb for sb in resp.json() if sb["code"] == bk_dev_sandbox.code][0]
        assert dev_sandbox["module_name"] == "default"
        assert dev_sandbox["version_info"] == {"version_name": "master", "version_type": "branch", "revision": "..."}


class StubVersionService:
    def list_alternative_versions(self) -> List[AlternativeVersion]:
        return [
            AlternativeVersion(
                name="master",
                type="branch",
                revision="...",
                url="https://github.com/example/helloworld.git",
            )
        ]


class TestCreateDevSandbox:
    """创建开发沙箱"""

    @pytest.fixture(autouse=True)
    def _mock_patch(self):
        mock_version_service = mock.MagicMock()
        mock_alternative_versions = [
            AlternativeVersion(
                name="master",
                type="branch",
                revision="...",
                url="https://github.com/example/helloworld.git",
            )
        ]
        mock_version_service.list_alternative_versions.return_value = mock_alternative_versions

        with (
            mock.patch(
                "paasng.accessories.dev_sandbox.serializers.get_version_service",
                return_value=mock_version_service,
            ),
            mock.patch(
                "paasng.accessories.dev_sandbox.views.upload_source_code",
                return_value="https://bkrepo.example.com/helloworld.zip",
            ),
            mock.patch(
                "paasng.accessories.dev_sandbox.views.get_env_vars_selected_addons",
                return_value={"FOO": "BAR"},
            ),
            mock.patch(
                "paasng.accessories.dev_sandbox.views.DevSandboxController.deploy",
                return_value=None,
            ),
        ):
            yield

    def test_create(self, api_client, bk_cnative_app, bk_module):
        resp = api_client.post(
            # 注：reverse 无法解析动态路由
            f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/dev_sandboxes/",
            data={
                "enable_code_editor": True,
                "inject_staging_env_vars": True,
                "source_code_version_info": {"version_type": "branch", "version_name": "master", "revision": "..."},
                "enabled_addons_services": ["mysql", "redis", "sentry"],
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["code"] is not None

    def test_create_simple(self, api_client, bk_cnative_app, bk_module):
        resp = api_client.post(
            f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/dev_sandboxes/",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["code"] is not None


class TestRetrieveDevSandbox:
    """获取开发沙箱详情"""

    @pytest.fixture(autouse=True)
    def _mock_patch(self):
        with mock.patch(
            "paasng.accessories.dev_sandbox.views.DevSandboxController.get_detail",
            return_value=DevSandboxDetail(
                workspace=DEV_SANDBOX_WORKSPACE,
                urls=DevSandboxUrls(base="example.com"),
                envs={"FOO": "BAR"},
                status=DevSandboxStatus.READY,
            ),
        ):
            yield

    def test_retrieve(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox):
        resp = api_client.get(
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            + f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {
            "workspace": "/data/workspace",
            "devserver_token": bk_dev_sandbox.token,
            "repo": {
                "url": "svn://127.0.0.1:8080/app/branch/master",
                "version_info": {"revision": "...", "version_name": "master", "version_type": "branch"},
            },
            "code_editor_password": bk_dev_sandbox.code_editor_config.password,
            "env_vars": {"FOO": "BAR"},
            "app_url": "example.com/app/",
            "devserver_url": "example.com/devserver/",
            "code_editor_url": "example.com/code_editor/",
            "status": "ready",
        }


class TestDestroyDevSandbox:
    """删除开发沙箱"""

    @pytest.fixture(autouse=True)
    def _mock_patch(self):
        with mock.patch("paasng.accessories.dev_sandbox.views.DevSandboxController.delete", return_value=None):
            yield

    def test_destroy(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox):
        resp = api_client.delete(
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            + f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/"
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT


class TestCommitDevSandbox:
    """沙箱代码提交"""

    @pytest.fixture(autouse=True)
    def _mock_patch(self):
        with mock.patch(
            "paasng.accessories.dev_sandbox.views.DevSandboxCodeCommit.commit",
            return_value="https://github.com/example/helloworld/tree/master",
        ):
            yield

    def test_commit(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox):
        resp = api_client.post(
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            + f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/commit/",
            data={"message": "this is my commit message!"},
        )
        assert resp.status_code == status.HTTP_200_OK


class TestEnvVarsDevSandbox:
    """沙箱环境变量"""

    @pytest.fixture(autouse=True)
    def _setup(self, bk_dev_sandbox):
        self.dev_sandbox = bk_dev_sandbox

    def test_upsert_env_vars_success(self, api_client, bk_cnative_app, bk_module, mocker):
        mock_upsert = mocker.patch("paasng.accessories.dev_sandbox.models.DevSandbox.upsert_env_vars")

        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{self.dev_sandbox.code}/upsert_env_vars/"
        )

        # 新增环境变量
        resp = api_client.post(url, {"env_vars": {"key": "NEW_VAR", "value": "new_value"}}, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        mock_upsert.assert_called_once_with(key="NEW_VAR", value="new_value")

        # 测试更新环境变量
        resp = api_client.post(url, {"env_vars": {"key": "NEW_VAR", "value": "updated_value"}}, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        mock_upsert.assert_called_with(key="NEW_VAR", value="updated_value")

    def test_upsert_env_vars_sandbox_not_found(self, api_client, bk_cnative_app, bk_module):
        invalid_code = "invalid123"
        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{invalid_code}/upsert_env_vars/"
        )

        resp = api_client.post(url, {"env_vars": {"key": "VALID_VAR", "value": "value"}}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "开发沙箱不存在" in resp.json()["detail"]

    def test_delete_env_var_success(self, api_client, bk_cnative_app, bk_module, mocker):
        mock_delete = mocker.patch("paasng.accessories.dev_sandbox.models.DevSandbox.delete_env_vars")

        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{self.dev_sandbox.code}/del_env_vars/"
        )

        resp = api_client.delete(url, {"key": "EXISTING_VAR"}, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        mock_delete.assert_called_once_with(key="EXISTING_VAR")

    def test_delete_env_var_missing_key(self, api_client, bk_cnative_app, bk_module):
        """测试缺少 key 参数的情况"""
        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{self.dev_sandbox.code}/del_env_vars/"
        )

        resp = api_client.delete(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

        response_data = resp.json()
        assert "fields_detail" in response_data
        assert "key" in response_data["fields_detail"]
        assert "该字段是必填项" in response_data["fields_detail"]["key"][0]

    def test_delete_env_var_sandbox_not_found(self, api_client, bk_cnative_app, bk_module):
        invalid_code = "invalid123"
        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{invalid_code}/del_env_vars/"
        )

        resp = api_client.delete(url, {"key": "EXISTING_VAR"}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "开发沙箱不存在" in resp.json()["detail"]
