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
from django.core.management import CommandError, call_command

from paasng.accessories.log.exceptions import TenantLogConfigNotFoundError
from paasng.accessories.log.models import TenantLogConfig
from paasng.accessories.log.shim.setup_bklog import BKLogConfigProvider
from paasng.core.tenant.user import get_init_tenant_id

pytestmark = pytest.mark.django_db


class TestBKLogConfigProvider:
    """测试 BKLogConfigProvider"""

    def test_config_not_exists(self, bk_module):
        """配置不存在时抛出异常"""
        TenantLogConfig.objects.filter(tenant_id=bk_module.application.tenant_id).delete()

        provider = BKLogConfigProvider(bk_module)
        with pytest.raises(TenantLogConfigNotFoundError):
            _ = provider.storage_cluster_id


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
        )

        config = TenantLogConfig.objects.get(tenant_id=tenant_id)
        assert config.storage_cluster_id == 200
        assert config.retention == 21
        assert config.es_shards == 5
        assert config.storage_replicas == 3
        assert config.time_zone == 2
