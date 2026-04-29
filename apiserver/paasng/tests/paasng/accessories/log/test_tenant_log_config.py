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

from paasng.accessories.log.exceptions import SharedBkBizIdNotConfiguredError, TenantLogConfigNotFoundError
from paasng.accessories.log.models import CustomCollectorConfig, TenantLogConfig
from paasng.accessories.log.shim.setup_bklog import BKLogConfigProvider
from paasng.accessories.log.shim.setup_bklog_shared import (
    _upsert_shared_custom_collector_config,
    should_use_shared_bk_log_index,
)
from paasng.core.tenant.user import get_init_tenant_id
from paasng.infras.bk_log.constatns import SHARED_INDEX_NAME_JSON_TEMPLATE, ETLType
from paasng.infras.bk_log.definitions import AppLogCollectorConfig

pytestmark = pytest.mark.django_db


class TestBKLogConfigProvider:
    """测试 BKLogConfigProvider"""

    @pytest.fixture()
    def bk_module_with_config(self, bk_module):
        """创建租户日志配置并关联到 bk_module"""
        TenantLogConfig.objects.filter(tenant_id=bk_module.application.tenant_id).delete()
        TenantLogConfig.objects.create(
            tenant_id=bk_module.application.tenant_id,
            storage_cluster_id=200,
            retention=21,
            es_shards=5,
            storage_replicas=3,
            time_zone=2,
            shared_bk_biz_id=42,
        )
        return bk_module

    def test_config_not_exists(self, bk_module):
        """配置不存在时抛出异常"""
        TenantLogConfig.objects.filter(tenant_id=bk_module.application.tenant_id).delete()

        provider = BKLogConfigProvider(bk_module)
        with pytest.raises(TenantLogConfigNotFoundError):
            _ = provider.storage_cluster_id

    def test_shared_bk_biz_id(self, bk_module_with_config):
        """获取已配置的 shared_bk_biz_id"""
        provider = BKLogConfigProvider(bk_module_with_config)
        assert provider.shared_bk_biz_id == 42

    def test_shared_bk_biz_id_not_configured(self, bk_module):
        """shared_bk_biz_id 未配置时抛出专用异常"""
        TenantLogConfig.objects.filter(tenant_id=bk_module.application.tenant_id).delete()
        TenantLogConfig.objects.create(
            tenant_id=bk_module.application.tenant_id,
            storage_cluster_id=200,
            retention=21,
            es_shards=5,
            storage_replicas=3,
            time_zone=2,
        )

        provider = BKLogConfigProvider(bk_module)
        with pytest.raises(SharedBkBizIdNotConfiguredError):
            _ = provider.shared_bk_biz_id


class TestShouldUseSharedBkLogIndex:
    """测试共享索引链路判定"""

    @override_settings(ENABLE_SHARED_BK_LOG_INDEX=True)
    def test_new_collector_uses_global_setting(self, bk_module):
        """没有历史内置采集项时, 使用全局开关决定是否创建共享索引"""
        assert should_use_shared_bk_log_index(bk_module) is True

    @override_settings(ENABLE_SHARED_BK_LOG_INDEX=False)
    def test_existing_shared_collector_ignores_global_setting(self, bk_module):
        """已有共享采集项时, 即使全局开关关闭也继续走共享链路"""
        self._create_builtin_collector(bk_module, SHARED_INDEX_NAME_JSON_TEMPLATE)

        assert should_use_shared_bk_log_index(bk_module) is True

    @override_settings(ENABLE_SHARED_BK_LOG_INDEX=True)
    def test_existing_independent_collector_ignores_global_setting(self, bk_module):
        """已有独立采集项时, 即使全局开关开启也继续走独立链路"""
        self._create_builtin_collector(bk_module, "foo_app__default__json")

        assert should_use_shared_bk_log_index(bk_module) is False

    def _create_builtin_collector(self, bk_module, name_en: str):
        """创建模块内置采集项"""
        return CustomCollectorConfig.objects.create(
            module=bk_module,
            name_en=name_en,
            collector_config_id=10001,
            index_set_id=20001,
            bk_data_id=30001,
            log_paths=[],
            log_type="json",
            is_builtin=True,
            is_enabled=True,
            tenant_id=bk_module.tenant_id,
        )


class TestCreateTenantLogConfigCommand:
    """测试 create_tenant_log_config 命令"""

    def test_rejects_mutually_exclusive_tenant_options(self) -> None:
        """`--tenant-id` 与 `--default-tenant` 不能同时指定"""
        with pytest.raises(CommandError):
            call_command(
                "create_tenant_log_config",
                "--tenant-id=foo",
                "--default-tenant",
                "--storage-cluster-id=1",
            )

    def test_create_config_for_default_tenant(self) -> None:
        """仅指定 `--default-tenant` 时应为初始化租户创建配置"""
        tenant_id = get_init_tenant_id()
        TenantLogConfig.objects.filter(tenant_id=tenant_id).delete()

        call_command(
            "create_tenant_log_config",
            "--default-tenant",
            "--storage-cluster-id=200",
            "--retention=21",
            "--es-shards=5",
            "--storage-replicas=3",
            "--time-zone=2",
            "--shared-bk-biz-id=88",
        )

        config = TenantLogConfig.objects.get(tenant_id=tenant_id)
        assert config.storage_cluster_id == 200
        assert config.retention == 21
        assert config.es_shards == 5
        assert config.storage_replicas == 3
        assert config.time_zone == 2
        assert config.shared_bk_biz_id == 88

    def test_create_config_without_shared_bk_biz_id(self) -> None:
        """不指定 `--shared-bk-biz-id` 时, 字段应保持为 None"""
        tenant_id = get_init_tenant_id()
        TenantLogConfig.objects.filter(tenant_id=tenant_id).delete()

        call_command(
            "create_tenant_log_config",
            "--default-tenant",
            "--storage-cluster-id=200",
        )

        config = TenantLogConfig.objects.get(tenant_id=tenant_id)
        assert config.shared_bk_biz_id is None


class TestSharedCollectorConfigSetup:
    """测试共享采集项创建逻辑"""

    def test_upsert_shared_collector_uses_shared_bk_biz_id(self, bk_module):
        """共享采集项必须使用 tenant 的 shared_bk_biz_id，而不是应用监控空间 ID"""
        TenantLogConfig.objects.update_or_create(
            tenant_id=bk_module.application.tenant_id,
            defaults={
                "storage_cluster_id": 200,
                "retention": 21,
                "es_shards": 5,
                "storage_replicas": 3,
                "time_zone": 8,
                "shared_bk_biz_id": 9527,
            },
        )

        app_cfg = AppLogCollectorConfig(log_type="stdout", etl_type=ETLType.TEXT)

        with mock.patch(
            "paasng.accessories.log.shim.setup_bklog_shared.get_or_create_custom_collector_config"
        ) as mocked_get_or_create:
            mocked_get_or_create.return_value = mock.sentinel.collector

            result = _upsert_shared_custom_collector_config(bk_module, app_cfg)

        assert result is mock.sentinel.collector
        assert mocked_get_or_create.call_args.kwargs["biz_or_space_id"] == 9527
