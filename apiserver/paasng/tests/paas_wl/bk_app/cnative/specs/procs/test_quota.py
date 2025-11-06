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

from paas_wl.bk_app.cnative.specs.constants import (
    DEFAULT_PROC_CPU,
    DEFAULT_PROC_CPU_REQUEST,
    DEFAULT_PROC_MEM,
    DEFAULT_PROC_MEM_REQUEST,
)
from paas_wl.bk_app.cnative.specs.procs.quota import (
    is_available_res_quota_plan,
    parse_plan_to_limit_quota,
    parse_plan_to_request_quota,
)


# 本文件的测试不需要 Kubernetes 集群，覆盖父级的 autouse fixture
@pytest.fixture(scope="module", autouse=True)
def crds_is_configured():
    """覆盖父级 fixture，避免连接 k8s

    本文件中的测试是纯函数单元测试（资源配额解析），不需要 CRDs 配置
    """
    return True


class TestParsePlanToLimitQuota:
    """测试 parse_plan_to_limit_quota 函数（纯函数测试，不需要 k8s）"""

    @pytest.mark.parametrize(
        ("plan", "expected_cpu", "expected_memory"),
        [
            ("default", DEFAULT_PROC_CPU, DEFAULT_PROC_MEM),
            ("4C1G", "4000m", "1024Mi"),
            ("2C4G", "2000m", "4096Mi"),
            ("1C2G", "1000m", "2048Mi"),
            ("0.5C1G", "500m", "1024Mi"),
            ("2C0.5G", "2000m", "512Mi"),
        ],
    )
    def test_parse_plan_to_limit_quota_success(self, plan, expected_cpu, expected_memory):
        """测试 ResQuotaPlan 预定义方案和自定义方案"""
        quota = parse_plan_to_limit_quota(plan)
        assert quota.cpu == expected_cpu
        assert quota.memory == expected_memory

    @pytest.mark.parametrize(
        ("plan", "error_pattern"),
        [
            ("invalid", "Invalid custom quota plan format: invalid"),
            ("2X4Y", "Invalid custom quota plan format: 2X4Y"),
        ],
    )
    def test_parse_plan_to_limit_quota_failure(self, plan, error_pattern):
        """测试无效的资源配额方案格式会抛出异常"""
        with pytest.raises(ValueError, match=error_pattern):
            parse_plan_to_limit_quota(plan)


class TestParsePlanToRequestQuota:
    """测试 parse_plan_to_request_quota 函数（纯函数测试，不需要 k8s）"""

    @pytest.mark.parametrize(
        ("plan", "expected_cpu", "expected_memory"),
        [
            ("default", DEFAULT_PROC_CPU_REQUEST, DEFAULT_PROC_MEM_REQUEST),
            ("2C0.5G", "200m", "128Mi"),
            ("4C1G", "200m", "256Mi"),
            ("2C2G", "200m", "1024Mi"),
            ("0.5C2.5G", "200m", "1280Mi"),
            ("2C4G", "200m", "2048Mi"),
        ],
    )
    def test_parse_plan_to_request_quota_success(self, plan, expected_cpu, expected_memory):
        """测试 ResQuotaPlan 预定义方案和自定义方案"""
        quota = parse_plan_to_request_quota(plan)
        assert quota.cpu == expected_cpu
        assert quota.memory == expected_memory

    @pytest.mark.parametrize(
        ("plan", "error_pattern"),
        [
            ("invalid", "Invalid custom quota plan format: invalid"),
            ("2X4Y", "Invalid custom quota plan format: 2X4Y"),
        ],
    )
    def test_parse_plan_to_request_quota_failure(self, plan, error_pattern):
        """测试无效的资源配额方案格式会抛出异常"""
        with pytest.raises(ValueError, match=error_pattern):
            parse_plan_to_request_quota(plan)


@pytest.mark.skip_when_no_crds()
class TestIsAvailableResQuotaPlan:
    """测试 is_available_res_quota_plan 函数（纯函数测试，不需要 k8s）"""

    @pytest.mark.parametrize(
        ("plan", "expected"),
        [
            ("default", True),
            ("4C1G", True),
            ("2C4G", True),
            ("0.5C0.5G", True),
            ("invalid", False),
            ("2X4Y", False),
        ],
    )
    def test_is_available_res_quota_plan(self, plan, expected):
        """测试预定义方案有效"""
        assert is_available_res_quota_plan(plan) is expected
