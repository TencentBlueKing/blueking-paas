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

"""AppSpark 复用应用态部署、中断、日志接口的测试。

归属和预发布限制在两条入口各测一次：路径里带应用和环境的部署，以及路径里只有部署 ID 的日志。
"""

from unittest import mock

import pytest
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django_dynamic_fixture import G
from rest_framework import status

from paasng.misc.audit.constants import OperationEnum
from paasng.misc.audit.models import AppOperationRecord
from paasng.platform.applications.models import Application
from paasng.platform.engine.models import Deployment
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.constants import VersionType
from tests.paasng.platform.engine.setup_utils import create_fake_deployment
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _deploy_url(app_code: str, module_name: str, env: str = "prod") -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/envs/{env}/deployments/"


def _interrupt_url(app_code: str, module_name: str, deployment_id: str) -> str:
    return f"/sys/api/bkapps/applications/{app_code}/modules/{module_name}/deployments/{deployment_id}/interruptions/"


def _history_events_url(channel_id: str) -> str:
    return f"/sys/api/streams/{channel_id}/history_events"


@pytest.fixture()
def app_spark_app(bk_app: Application, bk_module: Module) -> Application:
    """默认模块来源为 AppSpark 的应用，即归 AppSpark 管理的应用。"""
    bk_module.source_origin = SourceOrigin.APP_SPARK
    bk_module.save(update_fields=["source_origin"])
    return bk_app


def make_extra_module(application: Application) -> Module:
    """Create a non-default module, as if the user added it in the Developer Center."""
    return G(
        Module,
        application=application,
        name="extra",
        is_default=False,
        source_origin=SourceOrigin.AUTHORIZED_VCS.value,
        region=application.region,
        tenant_id=application.tenant_id,
    )


@pytest.fixture()
def deploy_data() -> dict:
    """Request body for deploying a source package, the operator is a newly created user."""
    return {
        "version_type": VersionType.PACKAGE.value,
        "version_name": "0.0.1",
        "revision": "0.0.1",
        "operator": create_user().username,
    }


class TestAppSparkDeploy:
    """路径里带应用和环境：归属、默认模块、生产环境都在这里测。"""

    @pytest.fixture()
    def deployment(self, bk_module: Module) -> Deployment:
        """The deployment returned by the stubbed `initialize_deployment`."""
        return create_fake_deployment(bk_module, app_environment="prod")

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

    def test_deploy_prod(
        self, sys_app_spark_api_client, app_spark_app, bk_module: Module, deploy_data, deployment, initialize
    ):
        """AppSpark 可以把自己管理的应用部署到生产环境，操作人为请求体中的 operator。"""
        resp = sys_app_spark_api_client.post(_deploy_url(app_spark_app.code, bk_module.name), data=deploy_data)

        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert resp.json()["deployment_id"] == str(deployment.id)
        assert initialize.call_args.kwargs["operator"] == user_id_encoder.encode(
            settings.USER_TYPE, deploy_data["operator"]
        )

    def test_deploy_stag_rejected(
        self, sys_app_spark_api_client, app_spark_app, bk_module: Module, deploy_data, initialize
    ):
        """AppSpark 只能部署生产环境，预发布留给用户在开发者中心手动部署。"""
        resp = sys_app_spark_api_client.post(
            _deploy_url(app_spark_app.code, bk_module.name, env="stag"), data=deploy_data
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "SYSAPI_ENV_NOT_ALLOWED"
        initialize.assert_not_called()

    def test_not_app_spark_app_denied(
        self, sys_app_spark_api_client, bk_app, bk_module: Module, deploy_data, initialize
    ):
        """默认模块不是 AppSpark 来源时，应用不归 AppSpark 管理。"""
        bk_module.source_origin = SourceOrigin.AUTHORIZED_VCS
        bk_module.save(update_fields=["source_origin"])

        resp = sys_app_spark_api_client.post(_deploy_url(bk_app.code, bk_module.name), data=deploy_data)

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "APP_SPARK_APP_REQUIRED"
        initialize.assert_not_called()

    def test_non_default_module_denied(self, sys_app_spark_api_client, app_spark_app, deploy_data, initialize):
        """AppSpark 只能部署默认模块，用户在开发者中心新增的模块不归它管。"""
        extra_module = make_extra_module(app_spark_app)

        resp = sys_app_spark_api_client.post(_deploy_url(app_spark_app.code, extra_module.name), data=deploy_data)

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "APP_SPARK_MODULE_REQUIRED"
        initialize.assert_not_called()

    def test_aidev_on_app_spark_app_denied(
        self, sys_aidev_api_client, app_spark_app, bk_module: Module, deploy_data, initialize
    ):
        """AIDEV 不能操作 AppSpark 应用。"""
        resp = sys_aidev_api_client.post(_deploy_url(app_spark_app.code, bk_module.name), data=deploy_data)

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "AI_AGENT_APP_REQUIRED"


class TestAppSparkInterrupt:
    """应用态中断：不要求 operator 是部署发起人，AIDEV 也能中断自己的应用。"""

    def test_interrupt_by_other_operator(self, sys_app_spark_api_client, app_spark_app, bk_module: Module):
        """中断人不改部署记录上的发起人，单独记入操作记录。"""
        deployment = create_fake_deployment(bk_module)
        operator = create_user()

        resp = sys_app_spark_api_client.post(
            _interrupt_url(app_spark_app.code, bk_module.name, deployment.id), data={"operator": operator.username}
        )

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        deployment.refresh_from_db()
        assert deployment.operator != operator.pk
        assert deployment.build_int_requested_at is not None

        record = AppOperationRecord.objects.get(app_code=app_spark_app.code, operation=OperationEnum.INTERRUPT_DEPLOY)
        assert record.user == operator.pk
        assert record.environment == "prod"

    def test_aidev_interrupt_ai_agent_app(self, sys_aidev_api_client, bk_app, bk_module: Module):
        """AIDEV 也能中断 AI Agent 应用的部署，且不受 AppSpark 的生产环境限制。"""
        bk_app.is_ai_agent_app = True
        bk_app.save(update_fields=["is_ai_agent_app"])
        deployment = create_fake_deployment(bk_module, app_environment="stag")

        resp = sys_aidev_api_client.post(
            _interrupt_url(bk_app.code, bk_module.name, deployment.id), data={"operator": "admin"}
        )

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        deployment.refresh_from_db()
        assert deployment.build_int_requested_at is not None


class TestAppSparkStreamsHistoryEvents:
    """路径里只有部署 ID，按部署所在的应用和环境校验归属。"""

    @pytest.fixture()
    def subscriber(self):
        """Stub out the redis channel subscriber."""
        with mock.patch("paasng.platform.engine.streaming.views.StreamChannelSubscriber") as subscriber_cls:
            subscriber = subscriber_cls.return_value
            subscriber.get_channel_state.return_value = "running"
            subscriber.get_history_events.return_value = [{"id": 1, "event": "msg", "data": "hello"}]
            yield subscriber

    def test_read_own_prod_deployment(self, sys_app_spark_api_client, app_spark_app, bk_module: Module, subscriber):
        deployment = create_fake_deployment(bk_module, app_environment="prod")

        resp = sys_app_spark_api_client.get(_history_events_url(str(deployment.id)) + "?last_event_id=0")

        assert resp.status_code == status.HTTP_200_OK, resp.json()
        assert resp.json() == [{"id": 1, "event": "msg", "data": "hello"}]

    def test_ai_agent_app_denied(self, sys_app_spark_api_client, bk_app, bk_module: Module, subscriber):
        """同一个发布动作 AIDEV 和 AppSpark 都有，漏掉按部署反查归属就能读到对方的日志。"""
        bk_app.is_ai_agent_app = True
        bk_app.save(update_fields=["is_ai_agent_app"])
        deployment = create_fake_deployment(bk_module, app_environment="prod")

        resp = sys_app_spark_api_client.get(_history_events_url(str(deployment.id)))

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["code"] == "APP_SPARK_APP_REQUIRED"
        subscriber.get_history_events.assert_not_called()

    def test_stag_deployment_rejected(self, sys_app_spark_api_client, app_spark_app, bk_module: Module, subscriber):
        deployment = create_fake_deployment(bk_module, app_environment="stag")

        resp = sys_app_spark_api_client.get(_history_events_url(str(deployment.id)))

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["code"] == "SYSAPI_ENV_NOT_ALLOWED"
        subscriber.get_history_events.assert_not_called()
