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
from unittest.mock import patch

import pytest
from django.utils.timezone import now
from django_dynamic_fixture import G

from paasng.accessories.servicehub.constants import ServiceType
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import (
    DefaultPolicyCreationRecord,
    ServiceBindingPolicy,
    ServiceBindingPrecedencePolicy,
)
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.core.tenant.user import OP_TYPE_TENANT_ID
from paasng.platform.scheduler.jobs import _handel_single_service_default_policy, reconcile_e2b_sandboxes_job

pytestmark = pytest.mark.django_db


@pytest.fixture
def init_tenant_id():
    return OP_TYPE_TENANT_ID


@pytest.fixture()
def local_service(init_tenant_id):
    service = G(Service, name="test-service", category=G(ServiceCategory), logo_b64="dummy")
    G(Plan, name="plan-1", service=service, tenant_id=init_tenant_id)
    G(Plan, name="plan-2", service=service, tenant_id=init_tenant_id)
    return mixed_service_mgr.get(service.uuid)


class TestServiceDefaultPolicyInitialization:
    def test_skip_existing_policy(self, local_service, init_tenant_id):
        """测试已存在初始化记录则跳过初始化"""
        DefaultPolicyCreationRecord.objects.create(
            service_id=local_service.uuid, service_type=ServiceType.LOCAL, finished_at=now()
        )

        _handel_single_service_default_policy(local_service, init_tenant_id)
        # 验证没有新的分配策略被创建
        assert not ServiceBindingPolicy.objects.filter(service_id=local_service.uuid).exists()
        assert not ServiceBindingPrecedencePolicy.objects.filter(service_id=local_service.uuid).exists()

    def test_create_new_policy(self, local_service, init_tenant_id):
        """测试新策略创建流程"""
        _handel_single_service_default_policy(local_service, init_tenant_id)

        # 初始化记录已创建
        assert DefaultPolicyCreationRecord.objects.filter(service_id=local_service.uuid).exists()
        # 分配策略已创建
        assert ServiceBindingPolicy.objects.filter(service_id=local_service.uuid).exists()

    def test_skip_when_has_existing_policies(self, local_service, init_tenant_id):
        """测试已有策略时跳过初始化并自动创建初始化记录"""
        # 预先创建其他策略
        ServiceBindingPolicy.objects.create(
            service_id=local_service.uuid,
            service_type=ServiceType.LOCAL,
        )

        _handel_single_service_default_policy(local_service, init_tenant_id)

        # 验证没有重复创建分配记录
        assert ServiceBindingPolicy.objects.filter(service_id=local_service.uuid).count() == 1
        # 验证已经默认添加了初始化记录
        assert DefaultPolicyCreationRecord.objects.filter(service_id=local_service.uuid).exists()


class TestReconcileE2BSandboxesDispatch:
    """e2b 对账只在这里投递，重活由 celery worker 执行。"""

    @pytest.fixture()
    def delay(self):
        """拦下投递动作，避免测试依赖 broker。"""
        with patch("paasng.platform.agent_sandbox.e2b.tasks.reconcile_e2b_sandboxes_task.delay") as stub:
            yield stub

    def test_dispatches_when_the_period_is_claimed(self, delay):
        with patch("paasng.platform.scheduler.jobs.acquire_once_per_period", return_value=True):
            reconcile_e2b_sandboxes_job()

        delay.assert_called_once_with()

    def test_skips_when_another_process_already_dispatched(self, delay):
        """同一周期内其他进程已经投过，这里不能再投一条。"""
        with patch("paasng.platform.scheduler.jobs.acquire_once_per_period", return_value=False):
            reconcile_e2b_sandboxes_job()

        delay.assert_not_called()

    def test_period_follows_reconcile_interval(self, settings, delay):
        """周期键的存活时间必须与对账周期一致，否则一轮里会投出多条消息。"""
        settings.AGENT_SANDBOX_E2B_RECONCILE_INTERVAL_MINUTES = 7

        with patch("paasng.platform.scheduler.jobs.acquire_once_per_period", return_value=True) as claim:
            reconcile_e2b_sandboxes_job()

        claim.assert_called_once_with("periodic:reconcile_e2b_sandboxes", 7 * 60)
