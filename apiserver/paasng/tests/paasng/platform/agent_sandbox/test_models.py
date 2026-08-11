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

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from paas_wl.infras.cluster.constants import ClusterUsage
from paas_wl.infras.cluster.entities import AllocationContext
from paasng.platform.agent_sandbox.constants import SandboxStatus, SandboxWorkloadType
from paasng.platform.agent_sandbox.exceptions import SandboxAlreadyExists, SandboxCreateError
from paasng.platform.agent_sandbox.models import Sandbox

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestSandboxModel:
    """Test Sandbox model."""

    def test_sandbox_create_basic(self, bk_app, bk_user):
        """Test basic sandbox creation."""

        ttl_seconds = 2 * 60 * 60
        sandbox = Sandbox.objects.new(
            application=bk_app,
            creator=bk_user.pk,
            snapshot="python:3.11-alpine",
            name="test-sandbox",
            ttl_seconds=ttl_seconds,
        )

        assert sandbox.name == "test-sandbox"
        assert sandbox.snapshot == "python:3.11-alpine"
        assert sandbox.status == SandboxStatus.PENDING.value
        assert sandbox.workload_type == SandboxWorkloadType.DEFAULT.value
        assert sandbox.daemon_token is not None
        assert len(sandbox.daemon_token) == 32
        # 时间比较允许少量误差
        assert abs(sandbox.expired_at - (timezone.now() + timedelta(seconds=ttl_seconds))) < timedelta(seconds=1)

        # 显式传入 workload_type 时应落库
        si_sandbox = Sandbox.objects.new(
            application=bk_app,
            creator=bk_user.pk,
            snapshot="python:3.11-alpine",
            name="si-sandbox",
            workload_type=SandboxWorkloadType.SANDBOX_INSTANCE.value,
        )
        assert si_sandbox.workload_type == SandboxWorkloadType.SANDBOX_INSTANCE.value

    def test_raises_when_no_cluster(self, bk_app, bk_user):
        """No available cube cluster surfaces as SandboxCreateError (AC-005)."""
        with (
            mock.patch(
                "paasng.platform.agent_sandbox.models.ClusterAllocator.get_default",
                side_effect=ValueError("no cluster found"),
            ),
            pytest.raises(SandboxCreateError, match="no available cluster"),
        ):
            Sandbox.objects.new(
                application=bk_app,
                creator=bk_user.pk,
                snapshot="python:3.11-alpine",
                name="no-cluster",
                workload_type=SandboxWorkloadType.SANDBOX_INSTANCE.value,
            )

    def test_sandbox_create_duplicate_name(self, bk_app, bk_user):
        """Test that creating sandbox with duplicate name raises error."""
        Sandbox.objects.new(
            application=bk_app,
            creator=bk_user.pk,
            snapshot="python:3.11-alpine",
            name="duplicate-name",
        )

        with pytest.raises(SandboxAlreadyExists):
            Sandbox.objects.new(
                application=bk_app,
                creator=bk_user.pk,
                snapshot="python:3.11-alpine",
                name="duplicate-name",
            )


def test_create_for_agent_sandbox_usage_by_flag():
    """default -> AGENT_SANDBOX; for_sandbox_instance -> AI_AGENT_ISOLATED (temporary reuse)."""
    default_ctx = AllocationContext.create_for_agent_sandbox("tenant-1")
    assert default_ctx.usage == ClusterUsage.AGENT_SANDBOX

    si_ctx = AllocationContext.create_for_agent_sandbox("tenant-1", for_sandbox_instance=True)
    assert si_ctx.usage == ClusterUsage.AI_AGENT_ISOLATED
