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

from contextlib import suppress
from decimal import Decimal
from typing import Iterator
from unittest import mock

import pytest

from paas_wl.bk_app.agent_sandbox.constants import SandboxInstancePhase
from paas_wl.bk_app.agent_sandbox.kres_entities import (
    AgentSandboxInstance,
    AgentSandboxKresApp,
    AgentSandboxPod,
)
from paas_wl.utils.constants import PodPhase
from paasng.platform.agent_sandbox.constants import (
    DEFAULT_SANDBOX_CPU,
    DEFAULT_SANDBOX_MEMORY,
    SandboxStatus,
    SandboxWorkloadType,
)
from paasng.platform.agent_sandbox.exceptions import (
    SandboxCreateError,
    SandboxCreateTimeout,
    SandboxError,
    SandboxImageValidateError,
)
from paasng.platform.agent_sandbox.models import Sandbox, SandboxAppSettings, Volume
from paasng.platform.agent_sandbox.sandbox import (
    AgentSandboxResManager,
    create_sandbox,
    delete_sandbox,
    resolve_sandbox_resources,
)
from paasng.platform.agent_sandbox.workload import get_workload_handler

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def mock_sandbox_provision() -> Iterator[mock.MagicMock]:
    """Fixture that mocks AgentSandboxResManager.provision for sandbox creation tests.

    This fixture is useful for tests that need to create sandboxes without actually
    provisioning Kubernetes resources.

    :returns: The mock object for AgentSandboxResManager.provision.
    """
    from paasng.platform.agent_sandbox.sandbox import AgentSandboxResManager

    with mock.patch.object(AgentSandboxResManager, "provision") as mock_provision:
        mock_provision.return_value = mock.MagicMock()
        yield mock_provision


@pytest.fixture()
def mock_image_validator() -> Iterator[mock.MagicMock]:
    """Fixture that mocks check_snapshot_image_exists for sandbox creation tests.

    :returns: The mock object for check_snapshot_image_exists.
    """
    with mock.patch("paasng.platform.agent_sandbox.sandbox.check_snapshot_image_exists") as mock_check:
        yield mock_check


# TODO: 利用实际的集群资源来测试沙箱的创建
class TestCreateSandbox:
    """Test sandbox creation functionality."""

    def test_create_success(self, bk_app, bk_user, mock_sandbox_provision, mock_image_validator):
        """Test successful sandbox creation updates status to RUNNING."""
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="demo", env_vars={"FOO": "BAR"})

        sandbox.refresh_from_db()
        assert sandbox.status == SandboxStatus.RUNNING.value
        assert sandbox.started_at is not None
        assert sandbox.env_vars == {"FOO": "BAR"}
        assert sandbox.workload_type == SandboxWorkloadType.DEFAULT.value
        mock_sandbox_provision.assert_called_once()
        mock_image_validator.assert_not_called()

    def test_create_sandbox_instance_provisions_cr(self, bk_app, bk_user, mock_image_validator):
        """SandboxInstance workload creates SandboxInstance CR instead of Pod."""
        from paas_wl.bk_app.agent_sandbox import kres_entities as kres_mod

        with (
            mock.patch.object(kres_mod.agent_sandbox_instance_kmodel, "create") as mock_create_cr,
            mock.patch.object(kres_mod.agent_sandbox_pod_kmodel, "create") as mock_create_pod,
            mock.patch.object(kres_mod.agent_sandbox_svc_kmodel, "create") as mock_create_svc,
            mock.patch("paasng.platform.agent_sandbox.workload.SandboxInstanceWorkloadHandler.wait_until_ready"),
            mock.patch("paasng.platform.agent_sandbox.sandbox.NamespacesHandler"),
            mock.patch("paasng.platform.agent_sandbox.sandbox.ensure_image_credential"),
            mock.patch("paasng.platform.agent_sandbox.sandbox.get_router_endpoint", return_value="router.example.com"),
        ):
            sandbox = create_sandbox(
                application=bk_app,
                creator=bk_user.pk,
                name="si-demo",
                workload_type=SandboxWorkloadType.SANDBOX_INSTANCE.value,
            )

        assert sandbox.workload_type == SandboxWorkloadType.SANDBOX_INSTANCE.value
        assert sandbox.status == SandboxStatus.RUNNING.value
        mock_create_cr.assert_called_once()
        mock_create_pod.assert_not_called()
        mock_create_svc.assert_called_once()

    @pytest.mark.parametrize(
        "exc",
        [SandboxError("boom"), SandboxCreateTimeout("timeout")],
    )
    def test_create_resource_failed(self, bk_app, bk_user, mock_image_validator, exc):
        """provision 失败（含 wait 超时）时记录 ERR_CREATING，不写 started_at。"""
        with (
            suppress(SandboxError),
            mock.patch.object(AgentSandboxResManager, "provision", side_effect=exc),
        ):
            create_sandbox(application=bk_app, name="failed", creator=bk_user.pk)

        sandbox = Sandbox.objects.get(application=bk_app, name="failed")
        assert sandbox.status == SandboxStatus.ERR_CREATING.value
        assert sandbox.started_at is None

    @pytest.mark.usefixtures("mock_sandbox_provision", "mock_image_validator")
    def test_create_with_snapshot(self, bk_app, bk_user):
        """Test sandbox creation with custom snapshot."""
        sandbox = create_sandbox(
            application=bk_app,
            creator=bk_user.pk,
            name="with-snapshot",
            snapshot="custom-image:latest",
            snapshot_entrypoint=["python", "-m", "http.server"],
        )

        assert sandbox.snapshot == "custom-image:latest"
        assert sandbox.snapshot_entrypoint == ["python", "-m", "http.server"]

    def test_create_with_multiple_volume_mounts(self, bk_app, bk_user, settings, mock_sandbox_provision):
        """Test sandbox creation with multiple volume mounts."""
        settings.AGENT_SANDBOX_VOLUME_ENABLED = True

        vol1 = Volume.objects.create(application=bk_app, name="vol-a", tenant_id=bk_app.tenant_id)
        vol2 = Volume.objects.create(application=bk_app, name="vol-b", tenant_id=bk_app.tenant_id)
        mounts_input = [
            {"volume_id": str(vol1.uuid), "mount_path": "/workspace/data"},
            {"volume_id": str(vol2.uuid), "mount_path": "/workspace/models"},
        ]

        sandbox = create_sandbox(
            application=bk_app,
            creator=bk_user.pk,
            name="multi-volumes",
            volume_mounts=mounts_input,
        )

        sandbox.refresh_from_db()
        assert sandbox.status == SandboxStatus.RUNNING.value
        assert len(sandbox.volume_mounts) == 2
        assert sandbox.volume_mounts[0]["volume_id"] == str(vol1.uuid)
        assert sandbox.volume_mounts[1]["volume_id"] == str(vol2.uuid)


class TestResolveSandboxResources:
    """Test per-app sandbox resource resolution."""

    def test_fallback_to_platform_default(self, bk_app):
        """No per-app config -> platform default."""
        cpu, memory = resolve_sandbox_resources(bk_app)
        assert cpu == DEFAULT_SANDBOX_CPU
        assert memory == DEFAULT_SANDBOX_MEMORY

    def test_use_app_level_config(self, bk_app):
        """Per-app config overrides the platform default."""
        SandboxAppSettings.objects.create(
            application=bk_app,
            cpu=Decimal(4),
            memory=Decimal(2),
            tenant_id=bk_app.tenant_id,
        )
        cpu, memory = resolve_sandbox_resources(bk_app)
        assert cpu == Decimal(4)
        assert memory == Decimal(2)

    def test_partial_config_falls_back_per_field(self, bk_app):
        """Config exists but only sets cpu -> memory falls back to platform default."""
        SandboxAppSettings.objects.create(
            application=bk_app,
            cpu=Decimal(4),
            memory=None,
            tenant_id=bk_app.tenant_id,
        )
        cpu, memory = resolve_sandbox_resources(bk_app)
        assert cpu == Decimal(4)
        assert memory == DEFAULT_SANDBOX_MEMORY


class TestCreateSandboxResources:
    """Test that created sandbox records carry the resolved cpu/memory."""

    @pytest.mark.usefixtures("mock_sandbox_provision", "mock_image_validator")
    def test_create_uses_platform_default(self, bk_app, bk_user):
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="default-res")
        assert sandbox.cpu == DEFAULT_SANDBOX_CPU
        assert sandbox.memory == DEFAULT_SANDBOX_MEMORY

    @pytest.mark.usefixtures("mock_sandbox_provision", "mock_image_validator")
    def test_create_uses_app_level_config(self, bk_app, bk_user):
        SandboxAppSettings.objects.create(
            application=bk_app,
            cpu=Decimal(4),
            memory=Decimal(2),
            tenant_id=bk_app.tenant_id,
        )
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="custom-res")
        assert sandbox.cpu == Decimal(4)
        assert sandbox.memory == Decimal(2)


# TODO: 利用实际的集群资源来测试沙箱的删除
class TestDeleteSandbox:
    """Test sandbox deletion functionality."""

    @pytest.mark.usefixtures("mock_sandbox_provision")
    @pytest.mark.parametrize(
        "workload_type",
        [SandboxWorkloadType.DEFAULT.value, SandboxWorkloadType.SANDBOX_INSTANCE.value],
    )
    def test_delete_success(self, bk_app, bk_user, mock_image_validator, workload_type):
        """Deletion updates status to DELETED and passes the record's workload_type (AC-004)."""
        sandbox = create_sandbox(
            application=bk_app,
            creator=bk_user.pk,
            name=f"to-delete-{workload_type.replace('_', '-')}",
            workload_type=workload_type,
        )

        with mock.patch.object(AgentSandboxResManager, "destroy_by_name") as mock_destroy:
            delete_sandbox(sandbox)

            sandbox.refresh_from_db()
            assert sandbox.status == SandboxStatus.DELETED.value
            assert sandbox.deleted_at is not None
            mock_destroy.assert_called_once_with(sandbox.name, workload_type=workload_type)

    @pytest.mark.usefixtures("mock_sandbox_provision")
    def test_delete_resource_failed(self, bk_app, bk_user, mock_image_validator):
        """Test that failed resource deletion sets status to ERR_DELETING."""
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="delete-fail")

        with (
            suppress(SandboxError),
            mock.patch.object(
                AgentSandboxResManager,
                "destroy_by_name",
                side_effect=SandboxError("delete failed"),
            ),
        ):
            delete_sandbox(sandbox)

        sandbox.refresh_from_db()
        assert sandbox.status == SandboxStatus.ERR_DELETING.value
        assert sandbox.deleted_at is None


class TestImageValidation:
    """Test snapshot image existence validation during sandbox creation."""

    def test_create_raises_image_not_found(self, bk_app, bk_user):
        """Test that create_sandbox raises SandboxImageValidateError when image doesn't exist."""
        with (
            mock.patch(
                "paasng.platform.agent_sandbox.sandbox.check_snapshot_image_exists",
                side_effect=SandboxImageValidateError("image not found"),
            ),
            pytest.raises(SandboxImageValidateError, match="image not found"),
        ):
            create_sandbox(
                application=bk_app,
                creator=bk_user.pk,
                name="bad-image",
                snapshot="nonexistent:v1",
            )

        # No sandbox record should be created
        assert not Sandbox.objects.filter(application=bk_app, name="bad-image").exists()

    def test_create_skips_validation_for_default_image(self, bk_app, bk_user, mock_sandbox_provision):
        """Test that check_snapshot_image_exists is not called when using the default image."""
        with mock.patch("paasng.platform.agent_sandbox.sandbox.check_snapshot_image_exists") as mock_check:
            create_sandbox(application=bk_app, creator=bk_user.pk, name="default-image")

        # Should NOT be called when using the default image
        mock_check.assert_not_called()


class TestWaitForSandboxInstanceRunning:
    """Failed SandboxInstance must surface CR status diagnostics (H-1)."""

    def test_failed_includes_status_message_and_pod_logs(self, bk_app):
        kres_app = AgentSandboxKresApp(paas_app_id=bk_app.code, tenant_id=bk_app.tenant_id, target="default")
        handler = get_workload_handler(kres_app, SandboxWorkloadType.SANDBOX_INSTANCE.value)
        mock_client = mock.MagicMock()
        failed_status = mock.MagicMock(
            message="MicroVM boot failed: image pull error",
            podName="si-demo-xyz",
        )
        mock_si = mock.MagicMock()
        mock_si.wait_for_status.return_value = SandboxInstancePhase.FAILED.value
        mock_si.get.return_value = mock.MagicMock(status=failed_status)

        with (
            mock.patch.object(AgentSandboxKresApp, "get_kube_api_client") as mock_get_client,
            mock.patch("paasng.platform.agent_sandbox.workload.kres.KSandboxInstance", return_value=mock_si),
            mock.patch(
                "paasng.platform.agent_sandbox.workload.get_pod_logs",
                return_value="pull failed\n",
            ) as mock_pod_logs,
        ):
            mock_get_client.return_value.__enter__.return_value = mock_client
            with pytest.raises(SandboxCreateError) as exc_info:
                handler.wait_until_ready("si-demo", timeout=AgentSandboxResManager.create_timeout)

        assert exc_info.value.logs is not None
        assert "MicroVM boot failed: image pull error" in exc_info.value.logs
        assert "pull failed" in exc_info.value.logs
        assert "si-demo-xyz" not in exc_info.value.logs
        mock_pod_logs.assert_called_once_with(mock_client, kres_app.namespace, "si-demo-xyz")
        mock_si.wait_for_status.assert_called_once()
        assert mock_si.wait_for_status.call_args.kwargs["timeout"] == AgentSandboxResManager.create_timeout


class TestWorkloadHandler:
    """Workload routing decisions that no other layer covers."""

    @pytest.fixture()
    def kres_app(self, bk_app) -> AgentSandboxKresApp:
        """The KresApp that workload handlers are bound to."""
        return AgentSandboxKresApp(paas_app_id=bk_app.code, tenant_id=bk_app.tenant_id, target="default")

    def test_succeeded_pod_maps_to_stopped(self, kres_app):
        # restartPolicy=Never: daemon 正常退出后沙箱已不可用, 不能报成 running/pending
        handler = get_workload_handler(kres_app, SandboxWorkloadType.DEFAULT.value)
        assert handler.map_status(PodPhase.SUCCEEDED.value) == SandboxStatus.STOPPED.value

    def test_unknown_workload_type_is_rejected(self, kres_app):
        # 静默回退到 Pod 会用错资源类型读写/删除, 导致真实工作负载泄漏
        with pytest.raises(SandboxError, match="unsupported sandbox workload type"):
            get_workload_handler(kres_app, "microvm_v2")


class TestGetFromDbRecordRuntimePath:
    """get_from_db_record must preserve workload_type so destroy/status hit the right resource."""

    @pytest.mark.parametrize(
        ("workload_type", "entity_cls"),
        [
            (SandboxWorkloadType.DEFAULT.value, AgentSandboxPod),
            (SandboxWorkloadType.SANDBOX_INSTANCE.value, AgentSandboxInstance),
        ],
    )
    def test_builds_entity_by_workload_type(self, bk_app, bk_user, workload_type, entity_cls):
        sandbox = Sandbox.objects.new(
            application=bk_app,
            creator=bk_user.pk,
            snapshot="python:3.11-alpine",
            name=f"from-db-{workload_type.replace('_', '-')}",
            workload_type=workload_type,
        )
        with mock.patch(
            "paasng.platform.agent_sandbox.sandbox.get_router_endpoint",
            return_value="router.example.com",
        ):
            client = AgentSandboxResManager(bk_app, sandbox.target).get_from_db_record(sandbox)

        assert isinstance(client.entity, entity_cls)
        assert type(client.entity) is entity_cls
        assert client.entity.name == sandbox.name

    def test_sandbox_instance_destroy_and_status_use_cr(self, bk_app, bk_user):
        """SandboxInstance client must delete/read the CR, not the Pod API."""
        from paas_wl.bk_app.agent_sandbox import kres_entities as kres_mod

        sandbox = Sandbox.objects.new(
            application=bk_app,
            creator=bk_user.pk,
            snapshot="python:3.11-alpine",
            name="si-runtime",
            workload_type=SandboxWorkloadType.SANDBOX_INSTANCE.value,
        )
        with mock.patch(
            "paasng.platform.agent_sandbox.sandbox.get_router_endpoint",
            return_value="router.example.com",
        ):
            mgr = AgentSandboxResManager(bk_app, sandbox.target)
            client = mgr.get_from_db_record(sandbox)

        with (
            mock.patch.object(kres_mod.agent_sandbox_instance_kmodel, "delete_by_name") as mock_del_cr,
            mock.patch.object(kres_mod.agent_sandbox_pod_kmodel, "delete_by_name") as mock_del_pod,
            mock.patch.object(kres_mod.agent_sandbox_svc_kmodel, "delete_by_name"),
        ):
            mgr.destroy(client)

        mock_del_cr.assert_called_once()
        mock_del_pod.assert_not_called()
        # MicroVM teardown runs in sandbox-controller's finalizer, so the CR keeps its grace period
        assert mock_del_cr.call_args.kwargs["non_grace_period"] is False

        cr_status = mock.MagicMock(status=SandboxInstancePhase.CREATING.value)
        with (
            mock.patch.object(kres_mod.agent_sandbox_instance_kmodel, "get", return_value=cr_status) as mock_get_cr,
            mock.patch.object(kres_mod.agent_sandbox_pod_kmodel, "get") as mock_get_pod,
        ):
            assert client.get_status() == SandboxStatus.PENDING.value
            mock_get_cr.assert_called_once()
            mock_get_pod.assert_not_called()

    def test_resolve_pod_name_by_workload(self, bk_app, bk_user):
        """DEFAULT uses entity name; SandboxInstance requires status.podName."""
        with mock.patch(
            "paasng.platform.agent_sandbox.sandbox.get_router_endpoint",
            return_value="router.example.com",
        ):
            pod_sbx = Sandbox.objects.new(
                application=bk_app,
                creator=bk_user.pk,
                snapshot="python:3.11-alpine",
                name="pod-logs",
            )
            pod_client = AgentSandboxResManager(bk_app, pod_sbx.target).get_from_db_record(pod_sbx)
            assert pod_client._resolve_pod_name(mock.MagicMock()) == "pod-logs"

            si_sbx = Sandbox.objects.new(
                application=bk_app,
                creator=bk_user.pk,
                snapshot="python:3.11-alpine",
                name="si-logs",
                workload_type=SandboxWorkloadType.SANDBOX_INSTANCE.value,
            )
            si_client = AgentSandboxResManager(bk_app, si_sbx.target).get_from_db_record(si_sbx)

        mock_instance = mock.MagicMock()
        mock_instance.status.podName = "si-logs-from-status"
        mock_ksi = mock.MagicMock()
        mock_ksi.get.return_value = mock_instance
        with mock.patch("paasng.platform.agent_sandbox.workload.kres.KSandboxInstance", return_value=mock_ksi):
            assert si_client._resolve_pod_name(mock.MagicMock()) == "si-logs-from-status"

        mock_instance.status.podName = ""
        with (
            mock.patch("paasng.platform.agent_sandbox.workload.kres.KSandboxInstance", return_value=mock_ksi),
            pytest.raises(SandboxError, match="sandbox pod not found"),
        ):
            si_client._resolve_pod_name(mock.MagicMock())
