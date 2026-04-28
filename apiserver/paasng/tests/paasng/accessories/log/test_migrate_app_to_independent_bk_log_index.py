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
        """mock 掉 setup_env_log_model, 避免命令中真实触达 bk-log API"""
        target = (
            "paasng.accessories.log.management.commands.migrate_app_to_independent_bk_log_index.setup_env_log_model"
        )
        with mock.patch(target) as patched:
            yield patched

    @staticmethod
    def _make_collector_row(module, name_en: str, log_type: str) -> CustomCollectorConfig:
        return CustomCollectorConfig.objects.create(
            module=module,
            name_en=name_en,
            collector_config_id=hash(name_en) & 0xFFFF,
            index_set_id=0,
            bk_data_id=0,
            log_paths=[],
            log_type=log_type,
            is_builtin=True,
            is_enabled=True,
            tenant_id=module.tenant_id,
        )

    def test_app_not_found(self):
        """app-code 对应 Application 不存在时, 命令以 CommandError 退出"""
        with pytest.raises(CommandError):
            call_command("migrate_app_to_independent_bk_log_index", "--app-code=nonexistent-app")

    def test_dry_run_does_not_change_anything(self, bk_app, bk_module, patched_setup_env_log_model):
        """dry-run 不写 flag, 不改采集项行, 不调用 setup_env_log_model"""
        shared_row = self._make_collector_row(
            bk_module, PLATFORM_INDEX_NAME_JSON_TEMPLATE.format(tenant_id=bk_module.tenant_id), "json"
        )

        call_command("migrate_app_to_independent_bk_log_index", f"--app-code={bk_app.code}")

        assert not bk_app.feature_flag.has_feature(AppFeatureFlag.USE_INDEPENDENT_BK_LOG_INDEX)
        shared_row.refresh_from_db()
        assert shared_row.is_enabled is True
        patched_setup_env_log_model.assert_not_called()

    def test_real_run(self, bk_app, bk_module, patched_setup_env_log_model):
        """--no-dry-run: 置 flag、按 env 重跑 setup, 仅禁用 name 命中共享模板的行"""
        tenant_id = bk_module.tenant_id
        shared_json = self._make_collector_row(
            bk_module, PLATFORM_INDEX_NAME_JSON_TEMPLATE.format(tenant_id=tenant_id), "json"
        )
        shared_stdout = self._make_collector_row(
            bk_module, PLATFORM_INDEX_NAME_STDOUT_TEMPLATE.format(tenant_id=tenant_id), "stdout"
        )
        # 模拟独立路径下创建的采集项行, 命令不应误伤
        independent_row = self._make_collector_row(
            bk_module, f"{bk_app.code.replace('-', '_')}__default__json", "json"
        )

        call_command("migrate_app_to_independent_bk_log_index", f"--app-code={bk_app.code}", "--no-dry-run")

        assert bk_app.feature_flag.has_feature(AppFeatureFlag.USE_INDEPENDENT_BK_LOG_INDEX)
        # 默认 module 含 stag/prod 两个 env
        assert patched_setup_env_log_model.call_count == 2
        for row in (shared_json, shared_stdout, independent_row):
            row.refresh_from_db()
        assert shared_json.is_enabled is False
        assert shared_stdout.is_enabled is False
        assert independent_row.is_enabled is True
