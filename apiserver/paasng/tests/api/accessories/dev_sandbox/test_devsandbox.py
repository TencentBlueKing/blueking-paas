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
        resp = api_client.get(reverse("accessories.dev_sandbox.bulk", kwargs={"code": bk_cnative_app.code}))
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

        with mock.patch(
            "paasng.accessories.dev_sandbox.serializers.get_version_service",
            return_value=mock_version_service,
        ), mock.patch(
            "paasng.accessories.dev_sandbox.views.upload_source_code",
            return_value="https://bkrepo.example.com/helloworld.zip",
        ), mock.patch(
            "paasng.accessories.dev_sandbox.views.get_env_variables",
            return_value={"FOO": "BAR"},
        ), mock.patch(
            "paasng.accessories.dev_sandbox.views.DevSandboxController.deploy",
            return_value=None,
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

    def test_retrieve(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox, bk_code_editor):
        resp = api_client.get(
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            + f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {
            "workspace": "/data/workspace",
            "devserver_token": bk_dev_sandbox.token,
            "code_editor_password": bk_code_editor.password,
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
