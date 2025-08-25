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

"""Tests for Engine APIS"""

import logging
from unittest import mock

import pytest
from django.urls import reverse
from django_dynamic_fixture import G

from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.utils.query import get_latest_deploy_options
from paasng.platform.engine.workflow import DeploymentCoordinator
from paasng.platform.environments.constants import EnvRoleOperation
from paasng.platform.environments.models import EnvRoleProtection
from paasng.platform.sourcectl.constants import VersionType
from paasng.utils.masked_curlify import MASKED_CONTENT

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestConfigVarAPIs:
    def test_normal_create(self, api_client, bk_app, bk_module):
        api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
            {"key": "A1", "value": "foo", "environment_name": "_global_", "description": "bar"},
        )

        resp = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
        )
        assert len(resp.data) == 1
        assert resp.data[0]["key"] == "A1"
        assert resp.data[0]["description"] == "bar"

    def test_encrypted_create(self, api_client, bk_app, bk_module):
        # 测试加密 configvar 的创建
        api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
            {"key": "A1", "value": "foo", "is_sensitive": True, "environment_name": "_global_", "description": "bar"},
        )

        resp = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
        )
        assert len(resp.data) == 1
        assert resp.data[0]["key"] == "A1"
        assert resp.data[0]["value"] == MASKED_CONTENT
        assert resp.data[0]["description"] == "bar"
        assert resp.data[0]["is_sensitive"]

    def test_normal_edit(self, api_client, bk_app, bk_module):
        var_id = api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
            {"key": "A1", "value": "foo", "environment_name": "_global_", "description": "foo"},
        ).data["id"]

        api_client.put(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/{var_id}/",
            {"key": "A1", "value": "bar", "environment_name": "stag", "description": "bar"},
        )

        resp = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
        )
        assert resp.data[0]["value"] == "bar"
        assert resp.data[0]["description"] == "bar"

    def test_encrypted_edit(self, api_client, bk_app, bk_module):
        var_id = api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
            {"key": "A1", "value": "foo", "is_sensitive": True, "environment_name": "_global_", "description": "foo"},
        ).data["id"]

        api_client.put(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/{var_id}/",
            {"key": "A1", "value": "bar", "is_sensitive": True, "environment_name": "stag", "description": "bar"},
        )

        resp = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
        )
        assert resp.data[0]["description"] == "bar"
        assert resp.data[0]["value"] == MASKED_CONTENT

    def test_normal_delete(self, api_client, bk_app, bk_module):
        var_id = api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
            {"key": "A1", "value": "foo", "environment_name": "_global_"},
        ).data["id"]

        resp = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
        )
        assert len(resp.data) == 1

        api_client.delete(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/{var_id}/",
        )
        resp = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
        )
        assert len(resp.data) == 0

    def test_normal_var_copy(self, api_client, bk_app, bk_module):
        resp = api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/clone_from/{bk_module.name}"
        )
        assert resp.data["ignore_num"] == 0
        assert resp.data["create_num"] == 0
        assert resp.data["overwrited_num"] == 0
        api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/",
            {"key": "A1", "value": "foo", "environment_name": "_global_"},
        )
        resp = api_client.post(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/clone_from/{bk_module.name}"
        )
        assert resp.data["ignore_num"] == 1
        assert resp.data["overwrited_num"] == 0
        assert resp.data["create_num"] == 0

    def create_var_fixtures(self, api_client, bk_app, bk_module):
        """Create config var fixtures for testing purpose"""

        def create_var(payload):
            var_id = api_client.post(
                f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/", payload
            ).data["id"]
            return var_id

        create_var({"key": "S1", "value": "foo", "environment_name": "stag"})
        create_var({"key": "P1", "value": "foo", "environment_name": "prod"})
        create_var({"key": "S2", "value": "foo", "environment_name": "stag"})
        create_var({"key": "G1", "value": "foo", "environment_name": "_global_"})

    @pytest.mark.parametrize(
        ("order_by", "expected_keys"),
        [
            ("-created", ["G1", "S2", "P1", "S1"]),
            ("key", ["G1", "P1", "S1", "S2"]),
        ],
    )
    def test_list_order_by(self, api_client, bk_app, bk_module, order_by, expected_keys):
        self.create_var_fixtures(api_client, bk_app, bk_module)

        resp = api_client.get(
            f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/?order_by={order_by}",
        )
        keys = [item["key"] for item in resp.data]
        assert keys == expected_keys

    @pytest.mark.parametrize(
        ("environment_name", "expected_keys"),
        [
            ("", ["G1", "S2", "P1", "S1"]),
            ("stag", ["S2", "S1"]),
            ("prod", ["P1"]),
            ("_global_", ["G1"]),
        ],
    )
    def test_list_filter_environment_name(self, api_client, bk_app, bk_module, environment_name, expected_keys):
        self.create_var_fixtures(api_client, bk_app, bk_module)

        resp = api_client.get(
            (
                f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/"
                f"?environment_name={environment_name}"
            ),
        )
        keys = [item["key"] for item in resp.data]
        assert keys == expected_keys


class TestDeploymentViewSet:
    def test_deploy_not_allow(self, api_client, bk_app, bk_module, bk_stag_env):
        G(
            EnvRoleProtection,
            module_env=bk_stag_env,
            allowed_role=ApplicationRole.NOBODY,
            operation=EnvRoleOperation.DEPLOY.value,
        )
        url = reverse("api.deploy", kwargs={"code": bk_app.code, "environment": "stag"})
        resp = api_client.post(url, data={"version_type": "", "version_name": ""})
        assert resp.status_code == 400
        assert resp.json() == {
            "code": "RESTRICT_ROLE_DEPLOY_ENABLED",
            "detail": "已开启部署权限控制，仅管理员可以操作",
        }

    def test_deploy_no_revision(self, api_client, bk_app, bk_module):
        url = reverse("api.deploy", kwargs={"code": bk_app.code, "environment": "stag"})
        resp = api_client.post(url, data={"version_type": VersionType.BRANCH.value, "version_name": "bar"})
        assert resp.status_code == 400
        assert resp.json() == {"code": "CANNOT_GET_REVISION", "detail": "无法获取代码版本"}

    def test_deploy_with_image_type(self, api_client, bk_app, bk_module):
        url = reverse("api.deploy", kwargs={"code": bk_app.code, "environment": "stag"})
        resp = api_client.post(url, data={"version_type": VersionType.IMAGE.value, "version_name": "bar"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "version_type 为 image 时，revision 必须为 sha256 开头的镜像 digest"

    @pytest.mark.usefixtures("_init_tmpls")
    def test_deploy(self, api_client, bk_app_full, bk_module_full):
        url = reverse("api.deploy", kwargs={"code": bk_app_full.code, "environment": "stag"})
        with mock.patch("paasng.platform.engine.views.deploy.DeployTaskRunner"):
            resp = api_client.post(
                url, data={"version_type": VersionType.BRANCH.value, "version_name": "bar", "revision": "baz"}
            )

        coordinator = DeploymentCoordinator(bk_module_full.get_envs("stag"))
        deployment = coordinator.get_current_deployment()
        coordinator.release_lock()
        assert Deployment.objects.count() == 1
        assert resp.status_code == 201
        assert deployment is not None
        assert resp.json() == {"deployment_id": str(deployment.id), "stream_url": f"/streams/{deployment.id}"}

    def test_deploy_conflict(self, api_client, bk_app, bk_module, bk_stag_env):
        url = reverse("api.deploy", kwargs={"code": bk_app.code, "environment": "stag"})
        coordinator = DeploymentCoordinator(bk_stag_env)

        assert coordinator.acquire_lock()
        resp = api_client.post(
            url, data={"version_type": VersionType.BRANCH.value, "version_name": "bar", "revision": "baz"}
        )
        coordinator.release_lock()

        assert resp.status_code == 400
        assert resp.json() == {
            "code": "CANNOT_DEPLOY_ONGOING_EXISTS",
            "detail": "部署失败，已有部署任务进行中，请刷新查看",
        }

    def test_deploy_exception(self, api_client, bk_app, bk_module):
        url = reverse("api.deploy", kwargs={"code": bk_app.code, "environment": "stag"})
        resp = api_client.post(
            url, data={"version_type": VersionType.BRANCH.value, "version_name": "bar", "revision": "baz"}
        )
        assert resp.status_code == 400
        assert resp.json() == {"code": "CANNOT_DEPLOY_APP", "detail": "部署失败: 部署请求异常，请稍候再试"}


class TestDeployOptionsViewSet:
    @pytest.fixture
    def deploy_options(self, bk_app):
        return bk_app.deploy_options.create(replicas_policy="web_form_priority")

    def test_create(self, api_client, bk_app):
        assert bk_app.deploy_options.exists() is False

        url = reverse("api.deploy_options", kwargs={"code": bk_app.code})
        resp = api_client.post(url, data={"replicas_policy": "web_form_priority"})
        assert resp.status_code == 200
        assert resp.json() == {"replicas_policy": "web_form_priority"}
        deploy_options = get_latest_deploy_options(bk_app)
        assert deploy_options
        assert deploy_options.replicas_policy == "web_form_priority"

    def test_update(self, api_client, bk_app, deploy_options):
        assert deploy_options.replicas_policy == "web_form_priority"

        url = reverse("api.deploy_options", kwargs={"code": bk_app.code})
        resp = api_client.post(url, data={"replicas_policy": "app_desc_priority"})
        assert resp.status_code == 200
        assert resp.json() == {"replicas_policy": "app_desc_priority"}
        deploy_options = get_latest_deploy_options(bk_app)
        assert deploy_options
        assert deploy_options.replicas_policy == "app_desc_priority"

    def test_get(self, api_client, bk_app, deploy_options):
        url = reverse("api.deploy_options", kwargs={"code": bk_app.code})
        resp = api_client.get(url)
        assert resp.status_code == 200
        assert resp.json() == {"replicas_policy": deploy_options.replicas_policy}
