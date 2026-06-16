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

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from paasng.platform.agent_sandbox.models import SandboxAppendConfig

pytestmark = pytest.mark.django_db


class TestUpsertSandboxConfigCommand:
    """Test the upsert_sandbox_config management command."""

    def test_create_config(self, bk_app):
        call_command("upsert_sandbox_config", app_code=bk_app.code, cpu="4", memory="2")

        config = SandboxAppendConfig.objects.get(application=bk_app)
        assert config.cpu == Decimal("4")
        assert config.memory == Decimal("2")
        assert config.tenant_id == bk_app.tenant_id

    def test_create_with_cpu_only(self, bk_app):
        # 只传 cpu 时，memory 保持为空（创建沙箱时回退默认）
        call_command("upsert_sandbox_config", app_code=bk_app.code, cpu="4")

        config = SandboxAppendConfig.objects.get(application=bk_app)
        assert config.cpu == Decimal("4")
        assert config.memory is None

    def test_partial_update_keeps_other_field(self, bk_app):
        SandboxAppendConfig.objects.create(
            application=bk_app, cpu=Decimal("2"), memory=Decimal("1"), tenant_id=bk_app.tenant_id
        )
        # 只更新 memory，cpu 应保持原值不被覆盖
        call_command("upsert_sandbox_config", app_code=bk_app.code, memory="3")

        config = SandboxAppendConfig.objects.get(application=bk_app)
        assert config.cpu == Decimal("2")
        assert config.memory == Decimal("3")

    def test_update_existing_config(self, bk_app):
        SandboxAppendConfig.objects.create(
            application=bk_app, cpu=Decimal("2"), memory=Decimal("1"), tenant_id=bk_app.tenant_id
        )
        call_command("upsert_sandbox_config", app_code=bk_app.code, cpu="3", memory="2")

        config = SandboxAppendConfig.objects.get(application=bk_app)
        assert config.cpu == Decimal("3")
        assert config.memory == Decimal("2")

    def test_reset_config(self, bk_app):
        SandboxAppendConfig.objects.create(
            application=bk_app, cpu=Decimal("4"), memory=Decimal("2"), tenant_id=bk_app.tenant_id
        )
        call_command("upsert_sandbox_config", app_code=bk_app.code, reset=True)

        assert not SandboxAppendConfig.objects.filter(application=bk_app).exists()

    def test_reset_on_missing_config_is_noop(self, bk_app):
        # 未配置时 reset 不报错
        call_command("upsert_sandbox_config", app_code=bk_app.code, reset=True)
        assert not SandboxAppendConfig.objects.filter(application=bk_app).exists()

    def test_app_not_found(self):
        with pytest.raises(CommandError, match="does not exist"):
            call_command("upsert_sandbox_config", app_code="not-exist-app", cpu="2", memory="1")

    def test_missing_cpu_memory(self, bk_app):
        with pytest.raises(CommandError, match="required"):
            call_command("upsert_sandbox_config", app_code=bk_app.code)

    def test_invalid_cpu_value(self, bk_app):
        with pytest.raises(CommandError, match="Invalid cpu"):
            call_command("upsert_sandbox_config", app_code=bk_app.code, cpu="abc", memory="1")
