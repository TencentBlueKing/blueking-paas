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

import pytest

from paasng.platform.agent_sandbox.constants import SandboxStatus
from paasng.platform.agent_sandbox.exceptions import SandboxAlreadyExists
from paasng.platform.agent_sandbox.models import Sandbox

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestSandboxModel:
    """Test Sandbox model."""

    def test_sandbox_create_basic(self, bk_app, bk_user):
        """Test basic sandbox creation."""
        sandbox = Sandbox.objects.new(
            application=bk_app,
            creator=bk_user.pk,
            snapshot="python:3.11-alpine",
            name="test-sandbox",
        )

        assert sandbox.name == "test-sandbox"
        assert sandbox.snapshot == "python:3.11-alpine"
        assert sandbox.status == SandboxStatus.PENDING.value
        assert sandbox.daemon_host == "192.168.1.1"
        assert sandbox.daemon_port == 30001
        assert sandbox.daemon_token is not None
        assert len(sandbox.daemon_token) == 32

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
