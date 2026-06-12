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

import importlib
from collections.abc import Callable
from typing import Any

import pytest
from django.apps.registry import apps
from django.db import connection

from paasng.accessories.log.models import TenantLogConfig
from paasng.core.tenant.user import get_init_tenant_id

pytestmark = pytest.mark.django_db

MIGRATION_MODULE = "paasng.accessories.log.migrations.0009_init_tenantlogconfig_from_deprecated_bklog_config"


@pytest.fixture()
def run_init_tenant_log_config(monkeypatch) -> Callable[[dict[str, Any]], str]:
    """执行 0009 migration 的 init_tenant_log_config，并注入 BKLOG_CONFIG。"""

    migration = importlib.import_module(MIGRATION_MODULE)

    def _run(bklog_config: dict[str, Any]) -> str:
        monkeypatch.setattr(migration, "BKLOG_CONFIG", bklog_config)
        tenant_id = get_init_tenant_id()
        TenantLogConfig.objects.filter(tenant_id=tenant_id).delete()
        with connection.schema_editor() as schema_editor:
            migration.init_tenant_log_config(apps, schema_editor)
        return tenant_id

    return _run


def _base_bklog_config(storage_cluster_id: Any) -> dict[str, Any]:
    return {
        "STORAGE_CLUSTER_ID": storage_cluster_id,
        "RETENTION": 14,
        "ES_SHARDS": 1,
        "STORAGE_REPLICAS": 1,
        "TIME_ZONE": 8,
    }


class TestInitTenantLogConfigMigration:
    """测试 0009_init_tenantlogconfig_from_deprecated_bklog_config migration"""

    @pytest.mark.parametrize("storage_cluster_id", [8, "8"])
    def test_creates_config_when_storage_cluster_id_is_valid(
        self, run_init_tenant_log_config, storage_cluster_id
    ) -> None:
        """STORAGE_CLUSTER_ID 为整数或数字字符串时应创建默认租户配置"""
        tenant_id = run_init_tenant_log_config(_base_bklog_config(storage_cluster_id))

        config = TenantLogConfig.objects.get(tenant_id=tenant_id)
        assert config.storage_cluster_id == 8
        assert config.retention == 14
        assert config.es_shards == 1
        assert config.storage_replicas == 1
        assert config.time_zone == 8

    @pytest.mark.parametrize("storage_cluster_id", [None, "", "abc", 0])
    def test_skips_when_storage_cluster_id_is_invalid(self, run_init_tenant_log_config, storage_cluster_id) -> None:
        """STORAGE_CLUSTER_ID 缺失、非法或为零时不应创建配置"""
        tenant_id = run_init_tenant_log_config(_base_bklog_config(storage_cluster_id))

        assert not TenantLogConfig.objects.filter(tenant_id=tenant_id).exists()
