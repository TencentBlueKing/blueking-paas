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

from unittest import mock

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from paasng.accessories.log.models import CustomCollectorConfig
from paasng.accessories.log.shim import setup_env_log_model
from paasng.infras.bk_log.constatns import (
    PLATFORM_INDEX_NAME_JSON_TEMPLATE,
    PLATFORM_INDEX_NAME_STDOUT_TEMPLATE,
)
from paasng.platform.applications.constants import AppFeatureFlag

pytestmark = pytest.mark.django_db


@pytest.fixture()
def patched_shim_internals():
    """mock 掉 shim 里实际调用 bk-log API / DB 重写的下游函数, 仅观测路由"""
    with (
        mock.patch("paasng.accessories.log.shim.EnvClusterService") as fake_cluster_service,
        mock.patch("paasng.accessories.log.shim.setup_shared_bk_log_custom_collector") as fake_shared_collector,
        mock.patch("paasng.accessories.log.shim.setup_shared_bk_log_model") as fake_shared_model,
        mock.patch("paasng.accessories.log.shim.setup_bk_log_custom_collector") as fake_default_collector,
        mock.patch("paasng.accessories.log.shim.setup_default_bk_log_model") as fake_default_model,
    ):
        # 让集群命中 ENABLE_BK_LOG_COLLECTOR, 否则 collector 分支被跳过, 路由判断会缺一半信号
        fake_cluster_service.return_value.get_cluster.return_value.has_feature_flag.return_value = True
        yield {
            "shared_collector": fake_shared_collector,
            "shared_model": fake_shared_model,
            "default_collector": fake_default_collector,
            "default_model": fake_default_model,
        }


class TestSetupEnvLogModelRouting:
    """覆盖 setup_env_log_model 在共享开关 / App 豁免 flag 不同组合下的路由"""

    @pytest.fixture(autouse=True)
    def _enable_bk_log_for_app(self, bk_app, settings):
        """让 get_log_collector_type 返回 BK_LOG, 才会真的进 setup_*_bk_log_model 分支"""
        settings.ENABLE_BK_MONITOR = True
        bk_app.feature_flag.set_feature(AppFeatureFlag.ENABLE_BK_LOG_COLLECTOR, True)

    def test_shared_disabled_routes_to_independent(self, bk_stag_env, patched_shim_internals):
        """全局共享开关关闭时, 永远走独立路径"""
        with override_settings(ENABLE_SHARED_BK_LOG_INDEX=False):
            setup_env_log_model(bk_stag_env)

        patched_shim_internals["default_collector"].assert_called_once()
        patched_shim_internals["default_model"].assert_called_once()
        patched_shim_internals["shared_collector"].assert_not_called()
        patched_shim_internals["shared_model"].assert_not_called()

    def test_shared_enabled_without_flag_routes_to_shared(self, bk_stag_env, patched_shim_internals):
        """共享开关打开 + App 未豁免, 走共享路径"""
        with override_settings(ENABLE_SHARED_BK_LOG_INDEX=True):
            setup_env_log_model(bk_stag_env)

        patched_shim_internals["shared_collector"].assert_called_once()
        patched_shim_internals["shared_model"].assert_called_once()
        patched_shim_internals["default_collector"].assert_not_called()
        patched_shim_internals["default_model"].assert_not_called()

    def test_shared_enabled_with_flag_routes_to_independent(self, bk_app, bk_stag_env, patched_shim_internals):
        """共享开关打开 + App 已置 USE_INDEPENDENT_BK_LOG_INDEX, 仍走独立路径"""
        bk_app.feature_flag.set_feature(AppFeatureFlag.USE_INDEPENDENT_BK_LOG_INDEX, True)

        with override_settings(ENABLE_SHARED_BK_LOG_INDEX=True):
            setup_env_log_model(bk_stag_env)

        patched_shim_internals["default_collector"].assert_called_once()
        patched_shim_internals["default_model"].assert_called_once()
        patched_shim_internals["shared_collector"].assert_not_called()
        patched_shim_internals["shared_model"].assert_not_called()


class TestMigrateAppToIndependentBkLogIndexCommand:
    """覆盖 migrate_app_to_independent_bk_log_index 命令"""

    @pytest.fixture()
    def patched_setup_env_log_model(self):
        """命令调用 setup_env_log_model 会触发外部 bk-log API, 单测里 mock 掉"""
        target = (
            "paasng.accessories.log.management.commands.migrate_app_to_independent_bk_log_index.setup_env_log_model"
        )
        with mock.patch(target) as patched:
            yield patched

    def _make_shared_collector_rows(self, module) -> tuple[CustomCollectorConfig, CustomCollectorConfig]:
        """模拟该 module 之前在共享路径下产生的 CustomCollectorConfig 行"""
        tenant_id = module.tenant_id
        json_row = CustomCollectorConfig.objects.create(
            module=module,
            name_en=PLATFORM_INDEX_NAME_JSON_TEMPLATE.format(tenant_id=tenant_id),
            collector_config_id=1001,
            index_set_id=2001,
            bk_data_id=3001,
            log_paths=["/app/v3logs/*"],
            log_type="json",
            is_builtin=True,
            is_enabled=True,
            tenant_id=tenant_id,
        )
        stdout_row = CustomCollectorConfig.objects.create(
            module=module,
            name_en=PLATFORM_INDEX_NAME_STDOUT_TEMPLATE.format(tenant_id=tenant_id),
            collector_config_id=1002,
            index_set_id=2002,
            bk_data_id=3002,
            log_paths=[],
            log_type="stdout",
            is_builtin=True,
            is_enabled=True,
            tenant_id=tenant_id,
        )
        return json_row, stdout_row

    def test_app_not_found(self) -> None:
        """app-code 对应 Application 不存在时报错"""
        with pytest.raises(CommandError):
            call_command("migrate_app_to_independent_bk_log_index", "--app-code=nonexistent-app")

    def test_dry_run_does_not_change_anything(self, bk_app, bk_module, patched_setup_env_log_model) -> None:
        """dry-run 不修改 flag, 不改 CustomCollectorConfig, 不调用 setup_env_log_model"""
        json_row, stdout_row = self._make_shared_collector_rows(bk_module)

        call_command("migrate_app_to_independent_bk_log_index", f"--app-code={bk_app.code}")

        assert not bk_app.feature_flag.has_feature(AppFeatureFlag.USE_INDEPENDENT_BK_LOG_INDEX)
        json_row.refresh_from_db()
        stdout_row.refresh_from_db()
        assert json_row.is_enabled is True
        assert stdout_row.is_enabled is True
        patched_setup_env_log_model.assert_not_called()

    def test_real_run_sets_flag_and_disables_shared_rows(self, bk_app, bk_module, patched_setup_env_log_model) -> None:
        """--no-dry-run 时置 flag, 重跑每个 env, 并把共享行禁用"""
        json_row, stdout_row = self._make_shared_collector_rows(bk_module)

        call_command(
            "migrate_app_to_independent_bk_log_index",
            f"--app-code={bk_app.code}",
            "--no-dry-run",
        )

        assert bk_app.feature_flag.has_feature(AppFeatureFlag.USE_INDEPENDENT_BK_LOG_INDEX)

        # 该 App 默认 module 含 stag/prod 两个 env, setup_env_log_model 应被调两次
        assert patched_setup_env_log_model.call_count == 2

        json_row.refresh_from_db()
        stdout_row.refresh_from_db()
        assert json_row.is_enabled is False
        assert stdout_row.is_enabled is False

    def test_real_run_does_not_touch_independent_rows(self, bk_app, bk_module, patched_setup_env_log_model) -> None:
        """命令仅禁用 name_en 命中共享模板的行, 不影响独立采集项行"""
        independent_row = CustomCollectorConfig.objects.create(
            module=bk_module,
            name_en=f"{bk_app.code.replace('-', '_')}__default__json",
            collector_config_id=9001,
            index_set_id=9002,
            bk_data_id=9003,
            log_paths=["/app/v3logs/*"],
            log_type="json",
            is_builtin=True,
            is_enabled=True,
            tenant_id=bk_module.tenant_id,
        )

        call_command(
            "migrate_app_to_independent_bk_log_index",
            f"--app-code={bk_app.code}",
            "--no-dry-run",
        )

        independent_row.refresh_from_db()
        assert independent_row.is_enabled is True
