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
from unittest import mock

import pytest

from paas_wl.bk_app.agent_sandbox.constants import DEFAULT_TARGET
from paasng.platform.agent_sandbox.constants import SandboxStatus
from paasng.platform.agent_sandbox.exceptions import SandboxError
from paasng.platform.agent_sandbox.models import Sandbox
from paasng.platform.agent_sandbox.sandbox import AgentSandboxResManager, create_sandbox

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestCreateSandbox:
    def test_create_success(self, bk_app, bk_user):
        sandbox = create_sandbox(application=bk_app, creator=bk_user.pk, name="demo", env_vars={"FOO": "BAR"})
        try:
            sandbox.refresh_from_db()
            assert sandbox.status == SandboxStatus.RUNNING.value
            assert sandbox.started_at is not None
        finally:
            AgentSandboxResManager(bk_app, DEFAULT_TARGET).destroy_by_name("demo")
            sandbox.delete()

    def test_create_resource_failed(self, bk_app, bk_user):
        with (
            suppress(SandboxError),
            mock.patch(
                "paasng.platform.agent_sandbox.sandbox.AgentSandboxResManager.create",
                side_effect=SandboxError("boom"),
            ),
        ):
            create_sandbox(application=bk_app, name="failed", env_vars={"FOO": "BAR"}, creator=bk_user.pk)

        sandbox = Sandbox.objects.get(application=bk_app, name="failed")
        assert sandbox.status == SandboxStatus.ERR_CREATING.value
        assert sandbox.started_at is None
        sandbox.delete()
