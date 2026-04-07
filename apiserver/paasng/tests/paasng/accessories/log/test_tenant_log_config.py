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
from django.test.utils import override_settings

from paasng.accessories.log.exceptions import TenantLogConfigNotFoundError
from paasng.accessories.log.init_config import init_default_tenant_log_config
from paasng.accessories.log.models import TenantLogConfig
from paasng.accessories.log.shim.setup_bklog import BKLogConfigProvider
from paasng.core.tenant.user import get_init_tenant_id

pytestmark = pytest.mark.django_db


class TestInitDefaultTenantLogConfig:
    """测试初始化默认租户日志配置"""

    def test_create_from_settings(self, settings):
        """从 settings.BKLOG_CONFIG 创建配置"""
        with override_settings(
            BKLOG_CONFIG={
                "STORAGE_CLUSTER_ID": 100,
                "RETENTION": 30,
                "ES_SHARDS": 3,
                "STORAGE_REPLICAS": 2,
                "TIME_ZONE": 1,
            }
        ):
            default_tenant_id = get_init_tenant_id()
            TenantLogConfig.objects.filter(tenant_id=default_tenant_id).delete()

            init_default_tenant_log_config()

            config = TenantLogConfig.objects.get(tenant_id=default_tenant_id)
            assert config.storage_cluster_id == 100
            assert config.retention == 30
            assert config.es_shards == 3
            assert config.storage_replicas == 2
            assert config.time_zone == 1

    def test_error_log_if_missing_config(self, settings, caplog):
        with override_settings(BKLOG_CONFIG={}):
            default_tenant_id = get_init_tenant_id()
            TenantLogConfig.objects.filter(tenant_id=default_tenant_id).delete()

            init_default_tenant_log_config()

            assert "error" in caplog.text.lower()
            assert "miss" in caplog.text.lower()
            assert not TenantLogConfig.objects.filter(tenant_id=default_tenant_id).exists()

    def test_error_log_if_invalid_config_value(self, settings, caplog):
        with override_settings(
            BKLOG_CONFIG={
                "STORAGE_CLUSTER_ID": None,
                "RETENTION": 30,
                "ES_SHARDS": 3,
                "STORAGE_REPLICAS": 2,
                "TIME_ZONE": 1,
            }
        ):
            default_tenant_id = get_init_tenant_id()
            TenantLogConfig.objects.filter(tenant_id=default_tenant_id).delete()

            init_default_tenant_log_config()

            assert "invalid bklog_config" in caplog.text.lower()
            assert not TenantLogConfig.objects.filter(tenant_id=default_tenant_id).exists()


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
        )
        return bk_module

    def test_config_not_exists(self, bk_module):
        """配置不存在时抛出异常"""
        TenantLogConfig.objects.filter(tenant_id=bk_module.application.tenant_id).delete()

        provider = BKLogConfigProvider(bk_module)
        with pytest.raises(TenantLogConfigNotFoundError):
            _ = provider.storage_cluster_id
