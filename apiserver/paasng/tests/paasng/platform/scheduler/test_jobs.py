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
from unittest.mock import MagicMock, patch

import pytest
from django.utils.timezone import now
from django_dynamic_fixture import G

from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import (
    DefaultPolicyCreationRecord,
    ServiceBindingPolicy,
    ServiceBindingPrecedencePolicy,
)
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.core.tenant.user import OP_TYPE_TENANT_ID
from paasng.platform.scheduler.jobs import _handel_single_service_default_policy, redis_lock

pytestmark = pytest.mark.django_db


@pytest.fixture
def default_tenant_id():
    return OP_TYPE_TENANT_ID


@pytest.fixture()
def local_service(default_tenant_id):
    service = G(Service, name="test-service", category=G(ServiceCategory), logo_b64="dummy")
    G(Plan, name="plan-1", service=service, tenant_id=default_tenant_id)
    G(Plan, name="plan-2", service=service, tenant_id=default_tenant_id)
    return mixed_service_mgr.get(service.uuid)


class TestServiceDefaultPolicyInitialization:
    def test_skip_existing_policy(self, local_service, default_tenant_id):
        """测试已存在策略时跳过初始化"""
        DefaultPolicyCreationRecord.objects.create(
            service_id=local_service.uuid, service_type="local", finished_at=now()
        )

        _handel_single_service_default_policy(local_service, default_tenant_id)
        # 验证没有新策略被创建
        assert not ServiceBindingPolicy.objects.filter(service_id=local_service.uuid).exists()
        assert not ServiceBindingPrecedencePolicy.objects.filter(service_id=local_service.uuid).exists()

    def test_create_new_policy(self, local_service, default_tenant_id):
        """测试新策略创建流程"""
        _handel_single_service_default_policy(local_service, default_tenant_id)

        # 验证策略记录创建
        record = DefaultPolicyCreationRecord.objects.get(service_id=local_service.uuid)
        assert record is not None

        # 验证实际策略创建
        assert ServiceBindingPolicy.objects.filter(service_id=local_service.uuid).exists()

    def test_skip_when_has_existing_policies(self, local_service, default_tenant_id):
        """测试已有策略时跳过初始化"""
        # 预先创建其他策略
        ServiceBindingPolicy.objects.create(
            service_id=local_service.uuid,
            service_type="local",
        )

        _handel_single_service_default_policy(local_service, default_tenant_id)

        # 验证没有重复创建记录
        assert DefaultPolicyCreationRecord.objects.filter(service_id=local_service.uuid).count() == 1


class TestRedisLockBehavior:
    def test_lock_acquire_and_release(self):
        """测试锁的正常获取和释放"""
        mock_redis = MagicMock()
        mock_lock = MagicMock()
        # 正确模拟锁的获取结果和上下文管理器行为
        mock_lock.acquire.return_value = True
        mock_lock.__enter__.return_value = True
        mock_redis.lock.return_value = mock_lock

        with patch("paasng.platform.scheduler.jobs.get_default_redis", return_value=mock_redis):
            lock_key = "test:lock:key"
            with redis_lock(lock_key) as acquired:
                assert acquired is True
                mock_redis.lock.assert_called_once_with(
                    name=lock_key, timeout=300, blocking_timeout=0, thread_local=False
                )
            # 验证锁释放
            mock_lock.release.assert_called_once()

    def test_lock_not_acquired(self):
        """测试未能获取锁的情况"""
        mock_redis = MagicMock()
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False
        mock_redis.lock.return_value = mock_lock

        with patch("paasng.platform.scheduler.jobs.get_default_redis", return_value=mock_redis):
            lock_key = "test:lock:key"
            with redis_lock(lock_key) as acquired:
                assert acquired is False
