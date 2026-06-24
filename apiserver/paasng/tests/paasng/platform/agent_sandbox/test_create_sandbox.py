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

import uuid
from contextlib import suppress
from decimal import Decimal
from typing import Iterator
from unittest import mock

import pytest

from paasng.platform.agent_sandbox.constants import (
    DEFAULT_SANDBOX_CPU,
    DEFAULT_SANDBOX_MEMORY,
    SandboxStatus,
)
from paasng.platform.agent_sandbox.exceptions import SandboxError, SandboxImageValidateError
from paasng.platform.agent_sandbox.models import Sandbox, SandboxAppSettings, Volume
from paasng.platform.agent_sandbox.sandbox import (
    AgentSandboxResManager,
    _build_volume_mounts,
    create_sandbox,
    delete_sandbox,
    resolve_sandbox_resources,
)

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
        mock_sandbox_provision.assert_called_once()
        mock_image_validator.assert_not_called()

    def test_create_resource_failed(self, bk_app, bk_user, mock_image_validator):
        """Test that failed resource creation sets status to ERR_CREATING."""
        with (
            suppress(SandboxError),
            mock.patch.object(
                AgentSandboxResManager,
                "provision",
                side_effect=SandboxError("boom"),
            ),
        ):
            create_sandbox(application=bk_app, name="failed", env_vars={"FOO": "BAR"}, creator=bk_user.pk)

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
            cpu=Decimal("4"),
            memory=Decimal("2"),
            tenant_id=bk_app.tenant_id,
        )
        cpu, memory = resolve_sandbox_resources(bk_app)
        assert cpu == Decimal("4")
        assert memory == Decimal("2")

    def test_partial_config_falls_back_per_field(self, bk_app):
        """Config exists but only sets cpu -> memory falls back to platform default."""
        SandboxAppSettings.objects.create(
            application=bk_app,
            cpu=Decimal("4"),
            memory=None,
            tenant_id=bk_app.tenant_id,
        )
        cpu, memory = resolve_sandbox_resources(bk_app)
        assert cpu == Decimal("4")
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
            cpu=Decimal("4"),
            memory=Decimal("2"),
            tenant_id=bk_app.tenant_id,
        )
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="custom-res")
        assert sandbox.cpu == Decimal("4")
        assert sandbox.memory == Decimal("2")


# TODO: 利用实际的集群资源来测试沙箱的删除
class TestDeleteSandbox:
    """Test sandbox deletion functionality."""

    @pytest.mark.usefixtures("mock_sandbox_provision")
    def test_delete_success(self, bk_app, bk_user, mock_image_validator):
        """Test successful sandbox deletion updates status to DELETED."""
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="to-delete")

        with mock.patch.object(AgentSandboxResManager, "destroy_by_name") as mock_destroy:
            delete_sandbox(sandbox)

            sandbox.refresh_from_db()
            assert sandbox.status == SandboxStatus.DELETED.value
            assert sandbox.deleted_at is not None
            mock_destroy.assert_called_once_with("to-delete")

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


class TestBuildVolumeMounts:
    """Unit tests for _build_shared_volume_mounts with Volume DB lookup."""

    def test_looks_up_volume_and_builds_mount(self, bk_app, settings):
        settings.AGENT_SANDBOX_VOLUME_ENABLED = True

        volume = Volume.objects.create(
            application=bk_app,
            name="test-vol",
            tenant_id=bk_app.tenant_id,
        )

        result = _build_volume_mounts(
            bk_app,
            [{"volume_id": volume.uuid, "mount_path": "/workspace/shared"}],
        )
        assert len(result) == 1
        mount = result[0]
        assert mount.volume_id == str(volume.uuid)
        assert mount.mount_path == "/workspace/shared"
        assert mount.sub_path == f"app/{volume.uuid.hex}"
        assert mount.read_only is False

    def test_raises_when_volume_not_found(self, bk_app, settings):
        from paasng.utils.error_codes import error_codes

        settings.AGENT_SANDBOX_VOLUME_ENABLED = True

        fake_uuid = uuid.uuid4()
        with pytest.raises(type(error_codes.AGENT_SANDBOX_VOLUME_NOT_FOUND)):
            _build_volume_mounts(
                bk_app,
                [{"volume_id": fake_uuid, "mount_path": "/workspace/shared"}],
            )

    def test_skips_soft_deleted_volumes(self, bk_app, settings):
        from django.utils import timezone

        from paasng.utils.error_codes import error_codes

        settings.AGENT_SANDBOX_VOLUME_ENABLED = True

        volume = Volume.objects.create(
            application=bk_app,
            name="deleted-vol",
            tenant_id=bk_app.tenant_id,
            deleted_at=timezone.now(),
        )

        with pytest.raises(type(error_codes.AGENT_SANDBOX_VOLUME_NOT_FOUND)):
            _build_volume_mounts(
                bk_app,
                [{"volume_id": volume.uuid, "mount_path": "/workspace/shared"}],
            )

    def test_multiple_volumes_preserve_order(self, bk_app, settings):
        settings.AGENT_SANDBOX_VOLUME_ENABLED = True

        vol1 = Volume.objects.create(application=bk_app, name="vol-1", tenant_id=bk_app.tenant_id)
        vol2 = Volume.objects.create(application=bk_app, name="vol-2", tenant_id=bk_app.tenant_id)

        result = _build_volume_mounts(
            bk_app,
            [
                {"volume_id": vol2.uuid, "mount_path": "/opt/data"},
                {"volume_id": vol1.uuid, "mount_path": "/workspace/shared"},
            ],
        )
        assert len(result) == 2
        assert result[0].volume_id == str(vol2.uuid)
        assert result[1].volume_id == str(vol1.uuid)


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
