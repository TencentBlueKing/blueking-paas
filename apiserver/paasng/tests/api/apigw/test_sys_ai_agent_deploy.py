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

from dataclasses import dataclass
from unittest import mock

import pytest
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django_dynamic_fixture import G
from rest_framework import status

from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.models.offline import OfflineOperation
from paasng.platform.environments.constants import EnvRoleOperation
from paasng.platform.environments.models import EnvRoleProtection
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.constants import VersionType
from tests.paasng.platform.engine.setup_utils import create_fake_deployment
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

NON_AIDEV_CLIENTS = ["sys_api_client", "sys_lesscode_api_client"]


def _deploy_url(app_code: str, module_name: str, env: str = "stag") -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/envs/{env}/deployments/"


def _deploy_result_url(app_code: str, module_name: str, deployment_id: str) -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/deployments/{deployment_id}/result/"


def _history_events_url(channel_id: str) -> str:
    return f"/sys/api/streams/{channel_id}/history_events"


def _offline_url(app_code: str, module_name: str, env: str = "stag") -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/envs/{env}/offlines/"


def _offline_result_url(app_code: str, module_name: str, offline_id: str) -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/offlines/{offline_id}/result/"


@pytest.fixture()
def ai_agent_app(bk_app: Application) -> Application:
    """An AI Agent application."""
    bk_app.is_ai_agent_app = True
    bk_app.save(update_fields=["is_ai_agent_app"])
    return bk_app


@pytest.fixture()
def deploy_data() -> dict:
    """Request body for deploying, the operator is a newly created user."""
    return {
        "version_type": VersionType.BRANCH.value,
        "version_name": "bar",
        "revision": "baz",
        "operator": create_user().username,
    }


def _enable_admin_only_protection(env):
    """Only allow the administrators to deploy / offline the env."""
    G(
        EnvRoleProtection,
        module_env=env,
        allowed_role=ApplicationRole.ADMINISTRATOR,
        operation=EnvRoleOperation.DEPLOY.value,
    )


@dataclass
class FakeHint:
    reason: str = "fake reason"


class TestSysDeploy:
    """应用态部署接口测试"""

    @pytest.fixture()
    def deployment(self, bk_module: Module) -> Deployment:
        """The deployment returned by the stubbed `initialize_deployment`."""
        return create_fake_deployment(bk_module, app_environment="stag")

    @pytest.fixture()
    def initialize(self, deployment: Deployment):
        """Stub out the deploy task and the redis lock, yield the mocked `initialize_deployment`."""
        with (
            mock.patch(
                "paasng.platform.engine.views.deploy.initialize_deployment", return_value=deployment
            ) as initialize,
            mock.patch("paasng.platform.engine.views.deploy.DeployTaskRunner"),
            mock.patch("paasng.platform.engine.views.deploy.DeploymentCoordinator") as coordinator_cls,
        ):
            coordinator_cls.return_value.acquire_lock.return_value = True
            yield initialize

    def test_deploy_success(
        self, sys_aidev_api_client, ai_agent_app, bk_module: Module, deploy_data: dict, deployment, initialize
    ):
        """AIDEV 可以用应用态凭证部署 AI Agent 应用，操作人为请求体中的 operator。"""
        resp = sys_aidev_api_client.post(_deploy_url(ai_agent_app.code, bk_module.name), data=deploy_data)

        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert resp.json() == {"deployment_id": str(deployment.id), "stream_url": f"/streams/{deployment.id}"}
        assert initialize.call_args.kwargs["operator"] == user_id_encoder.encode(
            settings.USER_TYPE, deploy_data["operator"]
        )

    def test_debug_not_allowed(self, sys_aidev_api_client, ai_agent_app, bk_module: Module, deploy_data: dict):
        """应用态部署不支持构建调试。"""
        deploy_data["advanced_options"] = {"debug_enabled": True}
        resp = sys_aidev_api_client.post(
            _deploy_url(ai_agent_app.code, bk_module.name), data=deploy_data, format="json"
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "CANNOT_DEPLOY_APP"
        assert not Deployment.objects.exists()

    def test_operator_role_not_checked(
        self, sys_aidev_api_client, ai_agent_app, bk_module: Module, bk_stag_env, deploy_data: dict, initialize
    ):
        """operator 仅做审计：即使环境开启了部署角色保护、operator 不是应用成员，也不查询 IAM、正常部署。"""
        _enable_admin_only_protection(bk_stag_env)
        with mock.patch("paasng.platform.engine.views.deploy.fetch_user_roles") as fetch_user_roles:
            resp = sys_aidev_api_client.post(_deploy_url(ai_agent_app.code, bk_module.name), data=deploy_data)

        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        fetch_user_roles.assert_not_called()

    @pytest.mark.parametrize("client_fixture", NON_AIDEV_CLIENTS)
    def test_non_aidev_client_denied(
        self, client_fixture: str, request: pytest.FixtureRequest, ai_agent_app, bk_module: Module, deploy_data: dict
    ):
        """非 AIDEV 调用方（含 BASIC_MAINTAINER / LESSCODE）返回 403。"""
        client = request.getfixturevalue(client_fixture)
        resp = client.post(_deploy_url(ai_agent_app.code, bk_module.name), data=deploy_data)

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app, bk_module: Module, deploy_data: dict):
        """对非 AI Agent 应用调用时返回 403。"""
        resp = sys_aidev_api_client.post(_deploy_url(bk_app.code, bk_module.name), data=deploy_data)

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"


class TestSysGetDeploymentResult:
    """应用态查询部署结果接口测试"""

    @pytest.fixture(autouse=True)
    def _patch_logs(self):
        with (
            mock.patch("paasng.platform.engine.views.deploy.get_all_logs", return_value="Deployment successful"),
            mock.patch("paasng.platform.engine.views.deploy.get_failure_hint", return_value=FakeHint()),
        ):
            yield

    def test_get_result_success(self, sys_aidev_api_client, ai_agent_app, bk_module: Module):
        """AIDEV 可以查询 AI Agent 应用的部署结果。"""
        deployment = create_fake_deployment(bk_module)
        resp = sys_aidev_api_client.get(_deploy_result_url(ai_agent_app.code, bk_module.name, deployment.id))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == deployment.status
        assert resp.json()["logs"] == "Deployment successful"

    @pytest.mark.parametrize("client_fixture", NON_AIDEV_CLIENTS)
    def test_non_aidev_client_denied(
        self, client_fixture: str, request: pytest.FixtureRequest, ai_agent_app, bk_module: Module
    ):
        """非 AIDEV 调用方返回 403。"""
        client = request.getfixturevalue(client_fixture)
        deployment = create_fake_deployment(bk_module)
        resp = client.get(_deploy_result_url(ai_agent_app.code, bk_module.name, deployment.id))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app, bk_module: Module):
        """对非 AI Agent 应用调用时返回 403。"""
        deployment = create_fake_deployment(bk_module)
        resp = sys_aidev_api_client.get(_deploy_result_url(bk_app.code, bk_module.name, deployment.id))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"


class TestSysStreamsHistoryEvents:
    """应用态获取部署日志接口测试"""

    @pytest.fixture()
    def subscriber(self):
        """Stub out the redis channel subscriber."""
        with mock.patch("paasng.platform.engine.streaming.views.StreamChannelSubscriber") as subscriber_cls:
            subscriber = subscriber_cls.return_value
            subscriber.get_channel_state.return_value = "running"
            subscriber.get_history_events.return_value = [{"id": 1, "event": "msg", "data": "hello"}]
            yield subscriber

    def test_get_events_success(self, sys_aidev_api_client, ai_agent_app, bk_module: Module, subscriber):
        """AIDEV 可以获取 AI Agent 应用的部署日志。"""
        deployment = create_fake_deployment(bk_module)
        resp = sys_aidev_api_client.get(_history_events_url(str(deployment.id)) + "?last_event_id=0")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [{"id": 1, "event": "msg", "data": "hello"}]
        subscriber.get_history_events.assert_called_once_with(last_event_id=0, ignore_special=False)

    @pytest.mark.parametrize("client_fixture", NON_AIDEV_CLIENTS)
    def test_non_aidev_client_denied(
        self, client_fixture: str, request: pytest.FixtureRequest, ai_agent_app, bk_module: Module, subscriber
    ):
        """非 AIDEV 调用方返回 403。"""
        client = request.getfixturevalue(client_fixture)
        deployment = create_fake_deployment(bk_module)
        resp = client.get(_history_events_url(str(deployment.id)))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app, bk_module: Module, subscriber):
        """部署所属应用不是 AI Agent 应用时返回 403。"""
        deployment = create_fake_deployment(bk_module)
        resp = sys_aidev_api_client.get(_history_events_url(str(deployment.id)))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"
        subscriber.get_history_events.assert_not_called()


class TestSysOffline:
    """应用态下架接口测试"""

    def test_offline_success(self, sys_aidev_api_client, ai_agent_app, bk_module: Module, bk_stag_env):
        """AIDEV 可以下架 AI Agent 应用，操作人为请求体中的 operator。"""
        operator = create_user()
        offline_op = OfflineOperation.objects.create(app_environment=bk_stag_env)
        with mock.patch(
            "paasng.platform.engine.views.misc.start_archive_step", return_value=offline_op
        ) as start_archive_step:
            resp = sys_aidev_api_client.post(
                _offline_url(ai_agent_app.code, bk_module.name), data={"operator": operator.username}
            )

        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert resp.json() == {"offline_operation_id": str(offline_op.id)}
        assert start_archive_step.call_args.kwargs["operator"] == user_id_encoder.encode(
            settings.USER_TYPE, operator.username
        )

    def test_operator_role_not_checked(self, sys_aidev_api_client, ai_agent_app, bk_module: Module, bk_stag_env):
        """operator 仅做审计：即使环境开启了部署角色保护、operator 不是应用成员，也不查询 IAM、正常下架。"""
        _enable_admin_only_protection(bk_stag_env)
        offline_op = OfflineOperation.objects.create(app_environment=bk_stag_env)
        with (
            mock.patch("paasng.platform.engine.views.misc.start_archive_step", return_value=offline_op),
            mock.patch("paasng.platform.engine.views.misc.fetch_user_roles") as fetch_user_roles,
        ):
            resp = sys_aidev_api_client.post(
                _offline_url(ai_agent_app.code, bk_module.name), data={"operator": create_user().username}
            )

        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        fetch_user_roles.assert_not_called()

    def test_operator_required(self, sys_aidev_api_client, ai_agent_app, bk_module: Module):
        """必须指定下架操作人。"""
        resp = sys_aidev_api_client.post(_offline_url(ai_agent_app.code, bk_module.name), data={})

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("client_fixture", NON_AIDEV_CLIENTS)
    def test_non_aidev_client_denied(
        self, client_fixture: str, request: pytest.FixtureRequest, ai_agent_app, bk_module: Module
    ):
        """非 AIDEV 调用方返回 403。"""
        client = request.getfixturevalue(client_fixture)
        resp = client.post(_offline_url(ai_agent_app.code, bk_module.name), data={"operator": "admin"})

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app, bk_module: Module):
        """对非 AI Agent 应用调用时返回 403。"""
        resp = sys_aidev_api_client.post(_offline_url(bk_app.code, bk_module.name), data={"operator": "admin"})

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"


class TestSysGetOfflineResult:
    """应用态查询下架结果接口测试"""

    @pytest.fixture()
    def offline_op(self, bk_app, bk_stag_env) -> OfflineOperation:
        """A succeeded offline operation of the stag env."""
        return OfflineOperation.objects.create(
            app_environment=bk_stag_env,
            operator=bk_app.owner,
            status="successful",
            source_location="svn://local-svn/app/trunk",
            source_version_type=VersionType.PACKAGE.value,
            source_version_name="0.0.1",
            source_revision="0.0.1",
            tenant_id=bk_app.tenant_id,
        )

    def test_get_result_success(self, sys_aidev_api_client, ai_agent_app, bk_module: Module, offline_op):
        """AIDEV 可以查询 AI Agent 应用的下架结果。"""
        resp = sys_aidev_api_client.get(_offline_result_url(ai_agent_app.code, bk_module.name, offline_op.id))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "successful"
        assert resp.json()["offline_operation_id"] == str(offline_op.id)

    @pytest.mark.parametrize("client_fixture", NON_AIDEV_CLIENTS)
    def test_non_aidev_client_denied(
        self, client_fixture: str, request: pytest.FixtureRequest, ai_agent_app, bk_module: Module, offline_op
    ):
        """非 AIDEV 调用方返回 403。"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get(_offline_result_url(ai_agent_app.code, bk_module.name, offline_op.id))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "SYSAPI_CLIENT_PERM_DENIED"

    def test_non_ai_agent_app_denied(self, sys_aidev_api_client, bk_app, bk_module: Module, offline_op):
        """对非 AI Agent 应用调用时返回 403。"""
        resp = sys_aidev_api_client.get(_offline_result_url(bk_app.code, bk_module.name, offline_op.id))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"
