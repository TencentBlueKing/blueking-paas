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
from django.core.cache import cache

from paas_wl.bk_app.cnative.specs.models import ResQuotaPlan, clear_quota_plans_cache, get_active_quota_plans
from paas_wl.bk_app.cnative.specs.models.quota_cache import CACHE_KEY_ACTIVE_PLANS

pytestmark = pytest.mark.django_db(databases=["workloads"])


@pytest.fixture(scope="session", autouse=True)
def crds_is_configured():
    """Override the crds_is_configured fixture to skip Kubernetes cluster connection.

    This test module only tests database and cache logic, no Kubernetes cluster is needed.
    """
    return False


class TestQuotaCache:
    """测试资源配额方案缓存功能"""

    def setup_method(self):
        """每个测试前清除缓存"""
        clear_quota_plans_cache()

    def test_get_active_quota_plans_returns_dict(self):
        """测试返回字典格式"""
        plans = get_active_quota_plans()
        assert isinstance(plans, dict)
        # 至少应该有 default 方案
        assert "default" in plans

    def test_get_active_quota_plans_caches_result(self):
        """测试结果被缓存"""
        # 第一次调用
        plans1 = get_active_quota_plans()

        # 缓存应该存在
        cached = cache.get(CACHE_KEY_ACTIVE_PLANS)
        assert cached is not None

        # 第二次调用应该从缓存获取
        plans2 = get_active_quota_plans()
        assert plans1 == plans2

    def test_cache_invalidation_on_create(self):
        """测试创建新方案时缓存被清除"""
        # 先获取一次，建立缓存
        plans_before = get_active_quota_plans()
        count_before = len(plans_before)

        # 创建新方案
        new_plan = ResQuotaPlan.objects.create(
            plan_name="test_8C8G",
            cpu_limit="8000m",
            memory_limit="8192Mi",
            cpu_request="400m",
            memory_request="4096Mi",
            is_active=True,
        )

        # 缓存应该被清除
        cached = cache.get(CACHE_KEY_ACTIVE_PLANS)
        assert cached is None

        # 重新获取应该包含新方案
        plans_after = get_active_quota_plans()
        assert len(plans_after) == count_before + 1
        assert "test_8C8G" in plans_after

        # 清理
        new_plan.delete()

    def test_cache_invalidation_on_update(self):
        """测试更新方案时缓存被清除"""
        # 先获取一次，建立缓存
        get_active_quota_plans()

        # 更新方案
        plan = ResQuotaPlan.objects.get(plan_name="default")
        plan.cpu_limit = "5000m"
        plan.save()

        # 缓存应该被清除
        cached = cache.get(CACHE_KEY_ACTIVE_PLANS)
        assert cached is None

    def test_cache_invalidation_on_delete(self):
        """测试删除方案时缓存被清除"""
        # 创建临时方案
        temp_plan = ResQuotaPlan.objects.create(
            plan_name="temp_plan",
            cpu_limit="2000m",
            memory_limit="2048Mi",
            cpu_request="100m",
            memory_request="512Mi",
            is_active=True,
        )

        # 先获取一次，建立缓存
        get_active_quota_plans()

        # 删除方案
        temp_plan.delete()

        # 缓存应该被清除
        cached = cache.get(CACHE_KEY_ACTIVE_PLANS)
        assert cached is None

    def test_only_active_plans_returned(self):
        """测试只返回激活的方案"""
        # 创建一个未激活的方案
        inactive_plan = ResQuotaPlan.objects.create(
            plan_name="inactive_plan",
            cpu_limit="1000m",
            memory_limit="1024Mi",
            cpu_request="100m",
            memory_request="256Mi",
            is_active=False,
        )

        plans = get_active_quota_plans()
        assert "inactive_plan" not in plans

        # 清理
        inactive_plan.delete()

    def test_clear_quota_plans_cache(self):
        """测试手动清除缓存"""
        # 建立缓存
        get_active_quota_plans()
        assert cache.get(CACHE_KEY_ACTIVE_PLANS) is not None

        # 清除缓存
        clear_quota_plans_cache()
        assert cache.get(CACHE_KEY_ACTIVE_PLANS) is None
