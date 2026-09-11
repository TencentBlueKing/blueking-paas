# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import string

import pytest
from bkpaas_auth.models import User
from django.test.utils import override_settings
from rest_framework import status

from paasng.core.tenant.constants import AppTenantMode
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import UserProfile
from paasng.platform.applications.constants import ApplicationType, DeployPolicy
from paasng.platform.applications.models import Application
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.modules.constants import SourceOrigin
from tests.utils.auth import create_user
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SYS_AI_AGENT_URL = "/sys/api/bkapps/ai_agent/"


@pytest.fixture()
def bk_app_code() -> str:
    # 应用态接口要求 ai- 前缀，总长仍落在 AppIDField 的 3-20 范围内。
    return f"ai-{generate_random_string(6, string.ascii_lowercase)}"


@pytest.fixture()
def bk_app_name() -> str:
    return generate_random_string(8)


@pytest.fixture()
def registered_operator() -> User:
    """已在开发者中心登录过的用户，具备 UserProfile。"""
    user = create_user()
    UserProfile.objects.create(user=user.pk, tenant_id=DEFAULT_TENANT_ID, role=SiteRole.USER.value)
    return user


def _assert_created_without_secret_or_deploy(resp, code: str, operator_username: str):
    """校验成功响应不含密钥、未部署、管理员仅为 operator。"""
    assert resp.status_code == status.HTTP_201_CREATED, f"error: {resp.json()}"
    body = resp.json()
    assert "bk_app_secret" not in body
    assert "secret" not in body

    application = Application.objects.get(code=code)
    assert application.get_administrators() == [operator_username]
    assert not Deployment.objects.filter(app_environment__application=application).exists()
    return body["application"], application


class TestSysCreateAIAgentApp:
    """应用态创建 AI Agent 应用接口测试"""

    @pytest.mark.usefixtures("_init_tmpls")
    def test_create_via_template(
        self,
        sys_aidev_api_client,
        mock_wl_services_in_creation,
        registered_operator,
        bk_app_code,
        bk_app_name,
    ):
        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={"code": bk_app_code, "name": bk_app_name, "operator": registered_operator.username},
        )
        app_data, _ = _assert_created_without_secret_or_deploy(resp, bk_app_code, registered_operator.username)
        assert app_data["modules"][0]["source_origin"] == SourceOrigin.AI_AGENT
        assert app_data["type"] == ApplicationType.CLOUD_NATIVE
        assert app_data["is_ai_agent_app"] is True
        assert app_data["is_plugin_app"] is True

    @pytest.mark.usefixtures("_init_tmpls")
    @pytest.mark.usefixtures("mock_initialize_vcs_with_template")
    @pytest.mark.parametrize(
        ("build_method", "extra_build_config", "is_isolated"),
        [
            ("dockerfile", {"dockerfile_path": "Dockerfile"}, False),
            ("buildpack", {}, False),
            ("dockerfile", {"dockerfile_path": "Dockerfile"}, True),
        ],
    )
    def test_create_via_git(
        self,
        sys_aidev_api_client,
        mock_wl_services_in_creation,
        registered_operator,
        bk_app_code,
        bk_app_name,
        build_method,
        extra_build_config,
        is_isolated,
    ):
        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": registered_operator.username,
                "is_isolated": is_isolated,
                "bkapp_spec": {"build_config": {"build_method": build_method, **extra_build_config}},
                "source_config": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        app_data, application = _assert_created_without_secret_or_deploy(
            resp, bk_app_code, registered_operator.username
        )
        assert app_data["type"] == ApplicationType.CLOUD_NATIVE
        assert app_data["is_ai_agent_app"] is True
        assert app_data["is_plugin_app"] is True
        assert app_data["modules"][0]["web_config"]["build_method"] == build_method

        expected_policy = DeployPolicy.ISOLATED.value if is_isolated else DeployPolicy.DEFAULT.value
        assert application.deploy_policy == expected_policy

    def test_create_engineless(
        self,
        sys_aidev_api_client,
        registered_operator,
        bk_app_code,
        bk_app_name,
    ):
        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": registered_operator.username,
                "is_engineless": True,
            },
        )
        app_data, _ = _assert_created_without_secret_or_deploy(resp, bk_app_code, registered_operator.username)
        assert app_data["type"] == ApplicationType.ENGINELESS_APP
        assert app_data["is_ai_agent_app"] is True
        assert app_data["is_plugin_app"] is False

    def test_basic_maintainer_denied(
        self,
        sys_api_client,
        registered_operator,
        bk_app_code,
        bk_app_name,
    ):
        # BASIC_MAINTAINER 有 MANAGE_APPLICATIONS，但不能调仅 AIDEV 可用的创建接口。
        resp = sys_api_client.post(
            SYS_AI_AGENT_URL,
            data={"code": bk_app_code, "name": bk_app_name, "operator": registered_operator.username},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert not Application.objects.filter(code=bk_app_code).exists()

    def test_operator_without_profile(
        self,
        sys_aidev_api_client,
        bk_app_code,
        bk_app_name,
    ):
        unregistered = create_user()
        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={"code": bk_app_code, "name": bk_app_name, "operator": unregistered.username},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert not Application.objects.filter(code=bk_app_code).exists()

    def test_code_without_ai_prefix(
        self,
        sys_aidev_api_client,
        registered_operator,
        bk_app_name,
    ):
        code = f"xx-{generate_random_string(6, string.ascii_lowercase)}"
        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={"code": code, "name": bk_app_name, "operator": registered_operator.username},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert not Application.objects.filter(code=code).exists()

    def test_duplicate_code(
        self,
        sys_aidev_api_client,
        registered_operator,
        bk_app_code,
        bk_app_name,
    ):
        first = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": registered_operator.username,
                "is_engineless": True,
            },
        )
        assert first.status_code == status.HTTP_201_CREATED

        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": generate_random_string(8),
                "operator": registered_operator.username,
                "is_engineless": True,
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert Application.objects.filter(code=bk_app_code).count() == 1

    def test_git_without_bkapp_spec(
        self,
        sys_aidev_api_client,
        registered_operator,
        bk_app_code,
        bk_app_name,
    ):
        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": registered_operator.username,
                "source_config": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_repo_auth_info": {},
                },
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert not Application.objects.filter(code=bk_app_code).exists()

    def test_git_auto_create_repo_rejected(
        self,
        sys_aidev_api_client,
        registered_operator,
        bk_app_code,
        bk_app_name,
    ):
        # 应用态不能借 operator 的 VCS OAuth 代建仓。
        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": registered_operator.username,
                "bkapp_spec": {"build_config": {"build_method": "buildpack"}},
                "source_config": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_control_type": "github",
                    "auto_create_repo": True,
                },
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert not Application.objects.filter(code=bk_app_code).exists()

    @pytest.mark.usefixtures("_init_tmpls")
    def test_git_write_template_to_repo_rejected(
        self,
        sys_aidev_api_client,
        registered_operator,
        bk_app_code,
        bk_app_name,
    ):
        # 应用态不能把模板推进 operator 名下的仓库。
        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": registered_operator.username,
                "bkapp_spec": {"build_config": {"build_method": "buildpack"}},
                "source_config": {
                    "source_origin": SourceOrigin.AUTHORIZED_VCS,
                    "source_repo_url": "https://github.com/octocat/helloWorld.git",
                    "source_init_template": "bk-ai-plugin-python",
                    "write_template_to_repo": True,
                },
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert not Application.objects.filter(code=bk_app_code).exists()

    @override_settings(ENABLE_MULTI_TENANT_MODE=True)
    def test_operator_tenant_mismatch(
        self,
        sys_aidev_api_client,
        bk_app_code,
        bk_app_name,
    ):
        operator = create_user()
        UserProfile.objects.create(user=operator.pk, tenant_id="foo", role=SiteRole.USER.value)

        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": operator.username,
                "is_engineless": True,
                "app_tenant_mode": AppTenantMode.SINGLE.value,
                "app_tenant_id": "bar",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert not Application.objects.filter(code=bk_app_code).exists()

    @override_settings(ENABLE_MULTI_TENANT_MODE=True)
    def test_global_app_requires_op_tenant_operator(
        self,
        sys_aidev_api_client,
        bk_app_code,
        bk_app_name,
    ):
        operator = create_user()
        UserProfile.objects.create(user=operator.pk, tenant_id="foo", role=SiteRole.USER.value)

        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": operator.username,
                "is_engineless": True,
                "app_tenant_mode": AppTenantMode.GLOBAL.value,
                "app_tenant_id": "",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert "operator" in resp.json()["fields_detail"]
        assert not Application.objects.filter(code=bk_app_code).exists()

    @override_settings(ENABLE_MULTI_TENANT_MODE=True)
    def test_operator_same_tenant_ok(
        self,
        sys_aidev_api_client,
        bk_app_code,
        bk_app_name,
    ):
        operator = create_user()
        UserProfile.objects.create(user=operator.pk, tenant_id="foo", role=SiteRole.USER.value)

        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": operator.username,
                "is_engineless": True,
                "app_tenant_mode": AppTenantMode.SINGLE.value,
                "app_tenant_id": "foo",
            },
        )
        app_data, application = _assert_created_without_secret_or_deploy(resp, bk_app_code, operator.username)
        assert app_data["type"] == ApplicationType.ENGINELESS_APP
        assert application.tenant_id == "foo"

    @override_settings(ENABLE_MULTI_TENANT_MODE=True)
    def test_global_app_with_op_operator_ok(
        self,
        sys_aidev_api_client,
        bk_app_code,
        bk_app_name,
    ):
        operator = create_user()
        UserProfile.objects.create(user=operator.pk, tenant_id=OP_TYPE_TENANT_ID, role=SiteRole.USER.value)

        resp = sys_aidev_api_client.post(
            SYS_AI_AGENT_URL,
            data={
                "code": bk_app_code,
                "name": bk_app_name,
                "operator": operator.username,
                "is_engineless": True,
                "app_tenant_mode": AppTenantMode.GLOBAL.value,
                "app_tenant_id": "",
            },
        )
        _, application = _assert_created_without_secret_or_deploy(resp, bk_app_code, operator.username)
        assert application.app_tenant_mode == AppTenantMode.GLOBAL
        assert application.tenant_id == OP_TYPE_TENANT_ID
