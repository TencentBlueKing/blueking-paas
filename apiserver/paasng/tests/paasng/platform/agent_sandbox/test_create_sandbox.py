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

from contextlib import suppress
from typing import Iterator
from unittest import mock

import pytest

from paasng.platform.agent_sandbox.constants import SandboxStatus
from paasng.platform.agent_sandbox.exceptions import SandboxError
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.sandbox import AgentSandboxResManager, create_sandbox, delete_sandbox

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


class TestCreateSandbox:
    """Test sandbox creation functionality."""

    def test_create_success(self, bk_app, bk_user, mock_sandbox_provision):
        """Test successful sandbox creation updates status to RUNNING."""
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="demo", env_vars={"FOO": "BAR"})

        sandbox.refresh_from_db()
        assert sandbox.status == SandboxStatus.RUNNING.value
        assert sandbox.started_at is not None
        assert sandbox.env_vars == {"FOO": "BAR"}
        mock_sandbox_provision.assert_called_once()

    def test_create_resource_failed(self, bk_app, bk_user):
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

    @pytest.mark.usefixtures("mock_sandbox_provision")
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


class TestDeleteSandbox:
    """Test sandbox deletion functionality."""

    @pytest.mark.usefixtures("mock_sandbox_provision")
    def test_delete_success(self, bk_app, bk_user):
        """Test successful sandbox deletion updates status to DELETED."""
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="to-delete")

        with mock.patch.object(AgentSandboxResManager, "destroy_by_name") as mock_destroy:
            delete_sandbox(sandbox)

            sandbox.refresh_from_db()
            assert sandbox.status == SandboxStatus.DELETED.value
            assert sandbox.deleted_at is not None
            mock_destroy.assert_called_once_with("to-delete")

    @pytest.mark.usefixtures("mock_sandbox_provision")
    def test_delete_resource_failed(self, bk_app, bk_user):
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
