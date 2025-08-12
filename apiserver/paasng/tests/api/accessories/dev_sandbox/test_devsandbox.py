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

    def test_upsert_env_vars_success(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox):
        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/env_vars/"
        )

        resp = api_client.post(url, {"key": "NEW_VAR", "value": "new_value"})
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        bk_dev_sandbox.refresh_from_db()
        updated_env_vars = bk_dev_sandbox.list_env_vars()
        updated_dict = {item["key"]: item["value"] for item in updated_env_vars}

        assert "NEW_VAR" in updated_dict
        assert updated_dict["NEW_VAR"] == "new_value"

        resp = api_client.post(url, {"key": "NEW_VAR", "value": "updated_value"})
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        bk_dev_sandbox.refresh_from_db()
        final_env_vars = bk_dev_sandbox.list_env_vars()
        final_dict = {item["key"]: item["value"] for item in final_env_vars}
        assert final_dict["NEW_VAR"] == "updated_value"

    def test_upsert_env_vars_sandbox_not_found(self, api_client, bk_cnative_app, bk_module):
        invalid_code = "invalid123"
        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{invalid_code}/env_vars/"
        )

        resp = api_client.post(url, {"key": "VALID_VAR", "value": "value"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_env_var_success(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox):
        env_var_url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/env_vars/"
        )

        # 添加环境变量
        api_client.post(env_var_url, {"key": "EXISTING_VAR", "value": "value"})
        bk_dev_sandbox.refresh_from_db()
        assert "EXISTING_VAR" in {item["key"] for item in bk_dev_sandbox.list_env_vars()}

        # 删除环境变量
        delete_url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/"
            f"env_vars/EXISTING_VAR/"
        )

        resp = api_client.delete(delete_url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # 验证环境变量已被删除
        bk_dev_sandbox.refresh_from_db()
        env_vars = bk_dev_sandbox.list_env_vars()
        env_var_keys = {item["key"] for item in env_vars}
        assert "EXISTING_VAR" not in env_var_keys

    def test_list_env_vars_success(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox):
        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/env_vars/"
        )
        api_client.post(url, {"key": "TEST_VAR1", "value": "value1"})
        api_client.post(url, {"key": "TEST_VAR2", "value": "value2"})
        resp = api_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [
            {"key": "TEST_VAR1", "value": "value1", "source": "custom"},
            {"key": "TEST_VAR2", "value": "value2", "source": "custom"},
        ]

    def test_list_env_vars_empty(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox):
        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/dev_sandboxes/{bk_dev_sandbox.code}/env_vars/"
        )
        resp = api_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []


class TestListDevSandboxAddonsServices:
    """测试获取沙箱使用的增强服务列表

    主要验证 addon_services_list API 的筛选逻辑：根据用户选择的增强服务列表过滤返回结果，因此这里简单模拟 Service 和 Rel 对象
    如果直接 mock 的话，需要模拟 get_service() 返回服务对象
    但是序列化器在访问 get_service().name 时，实际访问的是 MagicMock 对象的属性
    例如：
        assert {"<MagicMock name='mock.get_service.name' id='4750617488'>",\n "<MagicMock name='mock.get_service.name' id='4755145296'>"}
            == {'redis', 'mysql'}
    """

    def create_service_obj(self, name):
        """创建简单的服务对象"""

        class SimpleServiceObj:
            def __init__(self, name):
                self.name = name
                self.uuid = f"{name}-uuid"
                self.logo = f"{name}-logo"
                self.display_name = name.capitalize()
                self.description = f"{name} service"
                self.category = mock.MagicMock()

        return SimpleServiceObj(name)

    def create_rel_obj(self, service):
        """创建简单的关系对象"""

        class SimpleRelObj:
            def __init__(self, service):
                self.service = service

            def get_service(self):
                return self.service

        return SimpleRelObj(service)

    def test_with_enabled_services(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox, bk_user):
        bk_dev_sandbox.enabled_addons_services = ["mysql", "redis"]
        bk_dev_sandbox.save()

        mysql_service = self.create_service_obj("mysql")
        redis_service = self.create_service_obj("redis")
        sentry_service = self.create_service_obj("sentry")

        mysql_rel = self.create_rel_obj(mysql_service)
        redis_rel = self.create_rel_obj(redis_service)
        sentry_rel = self.create_rel_obj(sentry_service)

        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/"
            f"dev_sandboxes/{bk_dev_sandbox.code}/addons_services/"
        )

        # 模拟增强服务
        with (
            mock.patch(
                "paasng.accessories.dev_sandbox.views.mixed_service_mgr.list_provisioned_rels",
                return_value=[mysql_rel, redis_rel, sentry_rel],
            ),
        ):
            resp = api_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        assert {item["name"] for item in resp.json()} == {"mysql", "redis"}

    def test_with_no_enabled_services(self, api_client, bk_cnative_app, bk_module, bk_dev_sandbox, bk_user):
        bk_dev_sandbox.enabled_addons_services = []
        bk_dev_sandbox.save()

        mysql_service = self.create_service_obj("mysql")

        mysql_rel = self.create_rel_obj(mysql_service)

        url = (
            f"/api/bkapps/applications/{bk_cnative_app.code}/"
            f"modules/{bk_module.name}/"
            f"dev_sandboxes/{bk_dev_sandbox.code}/addons_services/"
        )

        # 模拟增强服务
        with mock.patch(
            "paasng.accessories.dev_sandbox.views.mixed_service_mgr.list_provisioned_rels", return_value=[mysql_rel]
        ):
            resp = api_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []
