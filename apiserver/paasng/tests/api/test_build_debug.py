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

from unittest import mock

import pytest

from paasng.platform.engine.models.deployment import AdvancedOptions
from tests.paasng.platform.engine.setup_utils import create_fake_deployment


def _make_pod_stub(phase, started=True):
    """创建模拟的 builder Pod 对象."""
    pod = mock.MagicMock()
    pod.status.phase = phase
    if started:
        c_status = mock.MagicMock()
        c_status.started = True
        pod.status.container_statuses = [c_status]
    else:
        pod.status.container_statuses = []
    return pod


pytestmark = pytest.mark.django_db


def _build_deploy_url(code: str, module_name: str) -> str:
    return f"/api/bkapps/applications/{code}/modules/{module_name}/envs/stag/deployments/"


def _build_debug_url(code: str, module_name: str, deployment_id: str) -> str:
    return f"/api/bkapps/applications/{code}/modules/{module_name}/deployments/{deployment_id}/build_debug/"


def _build_debug_console_url(code: str, module_name: str, deployment_id: str) -> str:
    return f"/api/bkapps/applications/{code}/modules/{module_name}/deployments/{deployment_id}/build_debug/console/"


@mock.patch("paasng.platform.engine.views.deploy.fetch_user_roles", return_value={"role": 3})
@mock.patch("paasng.platform.engine.views.deploy.env_role_protection_check")
@mock.patch("paasng.platform.engine.views.deploy.ModuleEnvDeployInspector")
class TestDeployWithBuildDebug:
    """测试部署时 build_debug 参数的校验."""

    def _deploy_payload(self, **overrides):
        base = {
            "version_type": "branch",
            "version_name": "master",
            "advanced_options": {},
        }
        base.update(overrides)
        return base

    def test_deploy_with_build_debug_not_cnb(
        self, mock_inspector, mock_role_check, mock_fetch_roles, api_client, bk_app, bk_module
    ):
        """非 CNB 构建方式开启 build_debug 应被拒绝."""
        mock_inspector.return_value.perform.return_value.activated = False
        url = _build_deploy_url(bk_app.code, bk_module.name)
        payload = self._deploy_payload(advanced_options={"build_debug": True})

        resp = api_client.post(url, data=payload, format="json")
        assert resp.status_code == 400
        assert "CNB" in resp.json().get("detail", "") or "cnb" in resp.json().get("detail", "").lower()

    def test_deploy_with_build_debug_bk_ci_pipeline(
        self, mock_inspector, mock_role_check, mock_fetch_roles, api_client, bk_app, bk_module
    ):
        """蓝盾流水线构建方式 + build_debug=True 应被拒绝."""
        mock_inspector.return_value.perform.return_value.activated = False
        # 设置模块使用蓝盾流水线构建
        bk_module.build_config.use_bk_ci_pipeline = True
        bk_module.build_config.save()

        url = _build_deploy_url(bk_app.code, bk_module.name)
        payload = self._deploy_payload(advanced_options={"build_debug": True})

        resp = api_client.post(url, data=payload, format="json")
        assert resp.status_code == 400


class TestGetBuildDebug:
    """测试 get_build_debug 接口."""

    def test_deployment_without_build_debug(self, api_client, bk_app, bk_module):
        """部署未开启 build_debug 时返回 enabled=False."""
        deployment = create_fake_deployment(bk_module)

        url = _build_debug_url(bk_app.code, bk_module.name, deployment.id)
        resp = api_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["available"] is False
        assert data["builder_pod_name"] is None
        assert data["namespace"] is None

    @pytest.mark.parametrize(
        "pod_phase",
        [None, "Pending"],
        ids=["no_pod", "pod_not_running"],
    )
    def test_build_debug_enabled_but_unavailable(self, api_client, bk_app, bk_module, pod_phase):
        """build_debug=True 但 Pod 不可用时返回 enabled=True, available=False."""
        deployment = create_fake_deployment(bk_module)
        deployment.advanced_options = AdvancedOptions(build_debug=True)
        deployment.save()

        pod = None
        if pod_phase is not None:
            pod = mock.MagicMock()
            pod.status.phase = pod_phase

        wl_app = mock.MagicMock()
        wl_app.namespace = "test-ns"

        with mock.patch(
            "paasng.platform.engine.views.deploy.DeploymentViewSet._get_debug_builder_pod",
            return_value=(wl_app, "builder-pod-name", pod),
        ):
            url = _build_debug_url(bk_app.code, bk_module.name, deployment.id)
            resp = api_client.get(url)
            assert resp.status_code == 200
            data = resp.json()
            assert data["enabled"] is True
            assert data["available"] is False
            assert data["builder_pod_name"] == "builder-pod-name"

    @pytest.mark.parametrize("window_available", [True, False], ids=["available", "expired"])
    def test_build_debug_window_check(self, api_client, bk_app, bk_module, window_available):
        """Pod Running 且构建已完成时, available 取决于调试窗口是否过期."""
        deployment = create_fake_deployment(bk_module)
        deployment.advanced_options = AdvancedOptions(build_debug=True)
        deployment.save()

        fake_pod = _make_pod_stub("Running")
        wl_app = mock.MagicMock()
        wl_app.namespace = "test-ns"

        with (
            mock.patch(
                "paasng.platform.engine.views.deploy.DeploymentViewSet._get_debug_builder_pod",
                return_value=(wl_app, "builder-pod-name", fake_pod),
            ),
            mock.patch(
                "paasng.platform.engine.views.deploy.BuildHandler.is_debug_window_available",
                return_value=window_available,
            ),
        ):
            url = _build_debug_url(bk_app.code, bk_module.name, deployment.id)
            resp = api_client.get(url)
            assert resp.status_code == 200
            data = resp.json()
            assert data["enabled"] is True
            assert data["available"] is window_available
            assert data["builder_pod_name"] == "builder-pod-name"
            assert data["namespace"] == "test-ns"

    def test_build_debug_build_in_progress(self, api_client, bk_app, bk_module):
        """Pod Running 但构建未完成 (started=False) 时返回 available=False."""
        deployment = create_fake_deployment(bk_module)
        deployment.advanced_options = AdvancedOptions(build_debug=True)
        deployment.save()

        fake_pod = _make_pod_stub("Running", started=False)
        wl_app = mock.MagicMock()
        wl_app.namespace = "test-ns"

        with mock.patch(
            "paasng.platform.engine.views.deploy.DeploymentViewSet._get_debug_builder_pod",
            return_value=(wl_app, "builder-pod-name", fake_pod),
        ):
            url = _build_debug_url(bk_app.code, bk_module.name, deployment.id)
            resp = api_client.get(url)
            assert resp.status_code == 200
            data = resp.json()
            assert data["enabled"] is True
            assert data["available"] is False


class TestCreateBuildDebugConsole:
    """测试 create_build_debug_console 接口."""

    @mock.patch("paasng.platform.engine.views.deploy.get_cluster_by_app")
    @mock.patch("paasng.platform.engine.views.deploy.bcs_client_cls")
    def test_create_console_success(self, mock_bcs_cls, mock_get_cluster, api_client, bk_app, bk_module):
        """正常创建 WebConsole 会话."""
        deployment = create_fake_deployment(bk_module)
        deployment.advanced_options = AdvancedOptions(build_debug=True)
        deployment.save()

        fake_pod = _make_pod_stub("Running")
        wl_app = mock.MagicMock()
        wl_app.namespace = "test-ns"

        # Setup BCS client mock
        mock_bcs_instance = mock.MagicMock()
        mock_bcs_instance.create_web_console_sessions.return_value = {
            "code": 0,
            "message": "success",
            "request_id": "req-123",
            "data": {"session_id": "session-456", "web_console_url": "https://console.example.com/session/456"},
        }
        mock_bcs_cls.return_value = mock_bcs_instance

        mock_get_cluster.return_value = mock.MagicMock(bcs_cluster_id="BCS-K8S-123", bcs_project_id="proj-456")

        with (
            mock.patch(
                "paasng.platform.engine.views.deploy.DeploymentViewSet._get_debug_builder_pod",
                return_value=(wl_app, "builder-pod-name", fake_pod),
            ),
            mock.patch(
                "paasng.platform.engine.views.deploy.BuildHandler.is_debug_window_available",
                return_value=True,
            ),
        ):
            url = _build_debug_console_url(bk_app.code, bk_module.name, deployment.id)
            resp = api_client.post(url)
            assert resp.status_code == 200
            data = resp.json()
            assert data["session_id"] == "session-456"
            assert "web_console_url" in data

    def test_create_console_pod_not_running(self, api_client, bk_app, bk_module):
        """Pod 不是 Running 状态时创建控制台应返回 400."""
        deployment = create_fake_deployment(bk_module)
        deployment.advanced_options = AdvancedOptions(build_debug=True)
        deployment.save()

        fake_pod = mock.MagicMock()
        fake_pod.status.phase = "Pending"

        with mock.patch(
            "paasng.platform.engine.views.deploy.DeploymentViewSet._get_debug_builder_pod",
            return_value=(mock.MagicMock(), "builder-pod-name", fake_pod),
        ):
            url = _build_debug_console_url(bk_app.code, bk_module.name, deployment.id)
            resp = api_client.post(url)
            assert resp.status_code == 400

    @mock.patch("paasng.platform.engine.views.deploy.get_cluster_by_app")
    @mock.patch("paasng.platform.engine.views.deploy.bcs_client_cls")
    def test_create_console_window_expired(self, mock_bcs_cls, mock_get_cluster, api_client, bk_app, bk_module):
        """调试窗口过期时创建控制台应返回 400."""
        deployment = create_fake_deployment(bk_module)
        deployment.advanced_options = AdvancedOptions(build_debug=True)
        deployment.save()

        fake_pod = _make_pod_stub("Running")

        with (
            mock.patch(
                "paasng.platform.engine.views.deploy.DeploymentViewSet._get_debug_builder_pod",
                return_value=(mock.MagicMock(), "builder-pod-name", fake_pod),
            ),
            mock.patch(
                "paasng.platform.engine.views.deploy.BuildHandler.is_debug_window_available",
                return_value=False,
            ),
        ):
            url = _build_debug_console_url(bk_app.code, bk_module.name, deployment.id)
            resp = api_client.post(url)
            assert resp.status_code == 400

    def test_create_console_build_in_progress(self, api_client, bk_app, bk_module):
        """构建进行中 (started=False) 时创建控制台应返回 400."""
        deployment = create_fake_deployment(bk_module)
        deployment.advanced_options = AdvancedOptions(build_debug=True)
        deployment.save()

        fake_pod = _make_pod_stub("Running", started=False)

        with mock.patch(
            "paasng.platform.engine.views.deploy.DeploymentViewSet._get_debug_builder_pod",
            return_value=(mock.MagicMock(), "builder-pod-name", fake_pod),
        ):
            url = _build_debug_console_url(bk_app.code, bk_module.name, deployment.id)
            resp = api_client.post(url)
            assert resp.status_code == 400
