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
import pytest

from paasng.plat_mgt.infras.services.serializers.binding_policies import AllocationPrecedencePolicySLZ


@pytest.mark.parametrize(
    ("data", "is_valid"),
    [
        # 非兜底规则允许不配置方案
        ({"matcher": {"usage_in": ["ai_agent"]}, "priority": 1, "plans": []}, True),
        # 兜底规则必须配置方案
        ({"matcher": {}, "priority": 0, "plans": []}, False),
        # 按环境分配时，任一环境的方案都不能为空
        ({"matcher": {"usage_in": ["ai_agent"]}, "priority": 1, "env_plans": {"stag": ["p1"], "prod": []}}, False),
    ],
)
def test_allocation_precedence_policy_slz(data, is_valid):
    assert AllocationPrecedencePolicySLZ(data=data).is_valid() is is_valid
