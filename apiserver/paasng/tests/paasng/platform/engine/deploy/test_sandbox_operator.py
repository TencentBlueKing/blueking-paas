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

import time
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import PollingMetadata, PollingStatus

from paas_wl.bk_app.cnative.specs.constants import BKPAAS_DEPLOY_ID_ANNO_KEY, DeployStatus
from paas_wl.bk_app.cnative.specs.crd.bk_app import (
    BkAppConfiguration,
    BkAppProcess,
    BkAppResource,
    BkAppSpec,
    DomainResolution,
    EnvOverlay,
    EnvVar,
    EnvVarOverlay,
    HostAlias,
    Schedule,
    Toleration,
)
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.bk_app.sandbox_instance.constants import SandboxInstancePhase
from paas_wl.bk_app.sandbox_instance.exceptions import SandboxInstanceNotFound
from paasng.platform.engine.deploy.bg_wait.wait_sandbox import WaitSandboxInstanceReady
from paasng.platform.engine.deploy.release.sandbox_operator import build_sandbox_spec_from_deploy
from tests.paas_wl.bk_app.cnative.specs.utils import create_cnative_deploy

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _make_bkapp_resource(
    processes=None, env_vars=None, env_overlay_vars=None, schedule=None, domain_resolution=None
):
    """构造一个最小化的 BkAppResource 用于测试。"""
    spec_kwargs = {
        "processes": processes or [],
        "configuration": BkAppConfiguration(env=env_vars or []),
    }
    if env_overlay_vars:
        spec_kwargs["envOverlay"] = EnvOverlay(envVariables=env_overlay_vars)
    if schedule:
        spec_kwargs["schedule"] = schedule
    if domain_resolution:
        spec_kwargs["domainResolution"] = domain_resolution

    return BkAppResource(
        metadata=ObjectMetadata(name="test-app"),
        spec=BkAppSpec(**spec_kwargs),
    )


# ============================================================================
# TestBuildSandboxSpecFromDeploy
# ============================================================================


@pytest.mark.usefixtures("_with_wl_apps")
class TestBuildSandboxSpecFromDeploy:
    """测试 build_sandbox_spec_from_deploy() 的字段映射逻辑。"""

    @pytest.fixture()
    def _mock_quota(self):
        """Mock ResQuotaPlan 查询返回固定值 cpu=4000m, memory=2048Mi"""
        fake_plan = mock.MagicMock()
        fake_plan.limits = {"cpu": "4000m", "memory": "2048Mi"}
        with mock.patch(
            "paasng.platform.engine.deploy.release.sandbox_operator.ResQuotaPlan.objects"
        ) as m:
            m.get.return_value = fake_plan
            yield

    @pytest.fixture()
    def build(self):
        """A mock Build object."""
        b = mock.MagicMock()
        b.image = "registry.example.com/app:v1"
        return b

    @pytest.fixture()
    def deployment(self):
        """A mock Deployment object."""
        return mock.MagicMock()

    def test_basic_fields(self, bk_stag_env, build, deployment, _mock_quota):
        """基本字段映射: image/command/args/cpu/memory/labels/annotations"""
        bkapp_res = _make_bkapp_resource(
            processes=[BkAppProcess(name="web", command=["python"], args=["-m", "app"])]
        )

        with (
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_bkapp_resource_for_deploy",
                return_value=bkapp_res,
            ),
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_process_selector",
                return_value={"app": "test"},
            ),
        ):
            spec = build_sandbox_spec_from_deploy(bk_stag_env, build, deployment, deploy_id="42")

        assert spec.image == "registry.example.com/app:v1"
        assert spec.command == ["python"]
        assert spec.args == ["-m", "app"]
        assert spec.cpu_cores == 4
        assert spec.memory == "2048Mi"
        assert spec.labels == {"app": "test"}
        assert spec.annotations == {BKPAAS_DEPLOY_ID_ANNO_KEY: "42"}

    def test_env_vars_global_and_overlay(self, bk_stag_env, build, deployment, _mock_quota):
        """环境变量: 全局变量 + overlay 覆盖合并"""
        bkapp_res = _make_bkapp_resource(
            processes=[BkAppProcess(name="web")],
            env_vars=[EnvVar(name="A", value="1"), EnvVar(name="B", value="2")],
            env_overlay_vars=[
                EnvVarOverlay(envName="stag", name="B", value="override"),
                EnvVarOverlay(envName="stag", name="C", value="3"),
                EnvVarOverlay(envName="prod", name="D", value="ignored"),
            ],
        )

        with (
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_bkapp_resource_for_deploy",
                return_value=bkapp_res,
            ),
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_process_selector",
                return_value={},
            ),
        ):
            spec = build_sandbox_spec_from_deploy(bk_stag_env, build, deployment, deploy_id="1")

        env_map = {e["name"]: e["value"] for e in spec.env_vars}
        assert env_map["A"] == "1"
        assert env_map["B"] == "override"
        assert env_map["C"] == "3"
        assert "D" not in env_map

    def test_env_overlay_only_current_env(self, bk_stag_env, build, deployment, _mock_quota):
        """overlay 仅取当前环境(stag)的变量, 忽略 prod"""
        bkapp_res = _make_bkapp_resource(
            processes=[BkAppProcess(name="web")],
            env_vars=[EnvVar(name="X", value="base")],
            env_overlay_vars=[
                EnvVarOverlay(envName="prod", name="X", value="prod_val"),
            ],
        )

        with (
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_bkapp_resource_for_deploy",
                return_value=bkapp_res,
            ),
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_process_selector",
                return_value={},
            ),
        ):
            spec = build_sandbox_spec_from_deploy(bk_stag_env, build, deployment, deploy_id="1")

        env_map = {e["name"]: e["value"] for e in spec.env_vars}
        # prod overlay 不应作用于 stag 环境
        assert env_map["X"] == "base"

    def test_scheduling(self, bk_stag_env, build, deployment, _mock_quota):
        """调度配置: nodeSelector / tolerations 透传"""
        bkapp_res = _make_bkapp_resource(
            processes=[BkAppProcess(name="web")],
            schedule=Schedule(
                nodeSelector={"gpu": "true"},
                tolerations=[Toleration(key="gpu", operator="Equal", value="true", effect="NoSchedule")],
            ),
        )

        with (
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_bkapp_resource_for_deploy",
                return_value=bkapp_res,
            ),
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_process_selector",
                return_value={},
            ),
        ):
            spec = build_sandbox_spec_from_deploy(bk_stag_env, build, deployment, deploy_id="1")

        assert spec.node_selector == {"gpu": "true"}
        assert len(spec.tolerations) == 1
        assert spec.tolerations[0]["key"] == "gpu"
        assert spec.tolerations[0]["effect"] == "NoSchedule"

    def test_domain_resolution(self, bk_stag_env, build, deployment, _mock_quota):
        """域名解析: dns_nameservers / host_aliases 透传"""
        bkapp_res = _make_bkapp_resource(
            processes=[BkAppProcess(name="web")],
            domain_resolution=DomainResolution(
                nameservers=["8.8.8.8", "8.8.4.4"],
                hostAliases=[HostAlias(ip="127.0.0.1", hostnames=["local.dev"])],
            ),
        )

        with (
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_bkapp_resource_for_deploy",
                return_value=bkapp_res,
            ),
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_process_selector",
                return_value={},
            ),
        ):
            spec = build_sandbox_spec_from_deploy(bk_stag_env, build, deployment, deploy_id="1")

        assert spec.dns_nameservers == ["8.8.8.8", "8.8.4.4"]
        assert spec.host_aliases == [{"ip": "127.0.0.1", "hostnames": ["local.dev"]}]

    def test_no_process_found(self, bk_stag_env, build, deployment, _mock_quota):
        """进程列表为空时: command/args 为空, 使用默认 quota"""
        bkapp_res = _make_bkapp_resource(processes=[])

        with (
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_bkapp_resource_for_deploy",
                return_value=bkapp_res,
            ),
            mock.patch(
                "paasng.platform.engine.deploy.release.sandbox_operator.get_process_selector",
                return_value={},
            ),
        ):
            spec = build_sandbox_spec_from_deploy(bk_stag_env, build, deployment, deploy_id="1")

        assert spec.command == []
        assert spec.args == []


# ============================================================================
# TestWaitSandboxInstanceReady
# ============================================================================


@pytest.mark.usefixtures("_with_wl_apps")
class TestWaitSandboxInstanceReady:
    """测试 WaitSandboxInstanceReady.get_status() 各种状态分支。"""

    @pytest.fixture()
    def metadata(self):
        return PollingMetadata(retries=0, query_started_at=time.time(), queried_count=0)

    @pytest.fixture()
    def app_model_deploy(self, bk_stag_env, bk_user):
        return create_cnative_deploy(bk_stag_env, bk_user, status=DeployStatus.PENDING)

    @pytest.fixture()
    def poller(self, bk_stag_env, app_model_deploy, metadata):
        return WaitSandboxInstanceReady(
            params={"env_id": bk_stag_env.id, "deploy_id": app_model_deploy.id},
            metadata=metadata,
        )

    def _mock_sandbox_manager(self, get_return=None, get_side_effect=None):
        """返回一个 context manager, mock SandboxInstanceManager"""
        mgr_instance = mock.MagicMock()
        if get_side_effect:
            mgr_instance.get.side_effect = get_side_effect
        else:
            mgr_instance.get.return_value = get_return
        return mock.patch(
            "paasng.platform.engine.deploy.bg_wait.wait_sandbox.SandboxInstanceManager",
            return_value=mgr_instance,
        )

    def _mock_cluster(self):
        return mock.patch(
            "paasng.platform.engine.deploy.bg_wait.wait_sandbox.EnvClusterService",
            return_value=mock.MagicMock(get_cluster_name=mock.MagicMock(return_value="default")),
        )

    def test_cr_not_found(self, poller):
        """CR 尚未存在时返回 doing()"""
        with self._mock_cluster(), self._mock_sandbox_manager(get_side_effect=SandboxInstanceNotFound("not found")):
            result = poller.get_status()

        assert result.status == PollingStatus.DOING

    def test_phase_running(self, poller, app_model_deploy):
        """phase=Running → done, state=READY"""
        cr = {
            "metadata": {"generation": 1, "annotations": {BKPAAS_DEPLOY_ID_ANNO_KEY: str(app_model_deploy.id)}},
            "status": {"phase": SandboxInstancePhase.RUNNING.value, "message": "ok", "observedGeneration": 1},
        }
        with self._mock_cluster(), self._mock_sandbox_manager(get_return=cr):
            result = poller.get_status()

        assert result.status == PollingStatus.DONE
        assert result.data["state"].status == DeployStatus.READY

    def test_phase_failed(self, poller, app_model_deploy):
        """phase=Failed → done, state=ERROR"""
        cr = {
            "metadata": {"generation": 1, "annotations": {BKPAAS_DEPLOY_ID_ANNO_KEY: str(app_model_deploy.id)}},
            "status": {"phase": SandboxInstancePhase.FAILED.value, "message": "OOM", "observedGeneration": 1},
        }
        with self._mock_cluster(), self._mock_sandbox_manager(get_return=cr):
            result = poller.get_status()

        assert result.status == PollingStatus.DONE
        assert result.data["state"].status == DeployStatus.ERROR

    def test_phase_pending(self, poller, app_model_deploy):
        """phase=Pending → doing, 且 update_status 被调用"""
        cr = {
            "metadata": {"generation": 1, "annotations": {BKPAAS_DEPLOY_ID_ANNO_KEY: str(app_model_deploy.id)}},
            "status": {"phase": SandboxInstancePhase.PENDING.value, "message": "pulling image", "observedGeneration": 1},
        }
        with (
            self._mock_cluster(),
            self._mock_sandbox_manager(get_return=cr),
            mock.patch("paasng.platform.engine.deploy.bg_wait.wait_sandbox.update_status") as mock_update,
        ):
            result = poller.get_status()

        assert result.status == PollingStatus.DOING
        assert result.data["phase"] == SandboxInstancePhase.PENDING.value
        assert mock_update.called

    def test_deploy_id_mismatch(self, poller, app_model_deploy):
        """CR annotation deploy_id 与期望不一致 → Abandoned"""
        cr = {
            "metadata": {"generation": 1, "annotations": {BKPAAS_DEPLOY_ID_ANNO_KEY: "99999"}},
            "status": {"phase": SandboxInstancePhase.RUNNING.value, "message": "", "observedGeneration": 1},
        }
        with self._mock_cluster(), self._mock_sandbox_manager(get_return=cr):
            result = poller.get_status()

        assert result.status == PollingStatus.DONE
        assert result.data["state"].status == DeployStatus.UNKNOWN

    def test_stale_observed_generation(self, poller, app_model_deploy):
        """observedGeneration != generation → doing(waiting_for_reconcile)"""
        cr = {
            "metadata": {"generation": 3, "annotations": {BKPAAS_DEPLOY_ID_ANNO_KEY: str(app_model_deploy.id)}},
            "status": {"phase": SandboxInstancePhase.RUNNING.value, "message": "", "observedGeneration": 2},
        }
        with self._mock_cluster(), self._mock_sandbox_manager(get_return=cr):
            result = poller.get_status()

        assert result.status == PollingStatus.DOING
        assert result.data.get("waiting_for_reconcile") is True
