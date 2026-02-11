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

import json

import pytest
from django_dynamic_fixture import G

from paasng.accessories.services.constants import PreCreatedInstanceAllocationType
from paasng.accessories.services.exceptions import InsufficientResourceError
from paasng.accessories.services.models import Plan, PreCreatedInstance

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True, params=[{"recyclable": True}, {}])
def bk_plan(request, bk_service):
    return G(Plan, config=json.dumps(request.param), service=bk_service)


class TestResourcePoolProvider:
    @pytest.fixture(params=[1, 3])
    def pools(self, request, bk_plan):
        result = []
        for i in range(request.param):
            result.append(G(PreCreatedInstance, plan=bk_plan, credentials=json.dumps({"idx": i})))
        return result

    def test_provision(self, bk_service, bk_plan, pools):
        instance = bk_service.create_service_instance_by_plan(bk_plan, {})
        assert json.loads(instance.credentials)["REDIS_IDX"] == json.loads(pools[0].credentials)["idx"]
        expect = PreCreatedInstance.objects.get(pk=pools[0].pk)
        assert instance.config.pop("__pk__") == str(expect.pk)
        assert instance.config == {
            "enable_tls": False,
            "is_pre_created": True,
            "provider_name": "redis",
            "recyclable": False,
        }
        assert expect.is_allocated

    def test_provision_with_str_config(self, bk_service, bk_plan):
        # 测试 config 为 str 类型时，能够正常运行
        ins = G(
            PreCreatedInstance, plan=bk_plan, config='{\n  "recyclable": true\n}\n', credentials=json.dumps({"idx": 0})
        )
        instance = bk_service.create_service_instance_by_plan(bk_plan, {})
        assert json.loads(instance.credentials)["REDIS_IDX"] == 0
        assert instance.config.pop("__pk__") == str(ins.pk)
        assert instance.config == {
            "enable_tls": False,
            "is_pre_created": True,
            "provider_name": "redis",
            "recyclable": True,
        }
        assert PreCreatedInstance.objects.get(pk=ins.pk).is_allocated

    def test_delete(self, bk_service, bk_plan, pools):
        instance = bk_service.create_service_instance_by_plan(bk_plan, {})
        assert PreCreatedInstance.objects.get(pk=pools[0].pk).is_allocated
        bk_service.delete_service_instance(instance)
        if json.loads(bk_plan.config).get("recyclable", False):
            assert not PreCreatedInstance.objects.get(pk=pools[0].pk).is_allocated
            assert PreCreatedInstance.objects.count() == len(pools)
        else:
            assert PreCreatedInstance.objects.get(pk=pools[0].pk).is_allocated
            assert PreCreatedInstance.objects.count() == len(pools)

    @pytest.mark.parametrize(
        ("policy_binding", "params", "expect_policy"),
        [
            pytest.param(
                # 完全匹配: 三个维度都命中
                {"app_code": ["myapp"], "module_name": ["default"], "env_name": ["prod"]},
                {"application_code": "myapp", "module_name": "default", "env_name": "prod"},
                True,
                id="exact_match_all_dimensions",
            ),
            pytest.param(
                # 通配维度: 策略只绑定 app_code, module_name/env_name 为空(通配)
                {"app_code": ["myapp"]},
                {"application_code": "myapp", "module_name": "default", "env_name": "prod"},
                True,
                id="wildcard_module_and_env",
            ),
            pytest.param(
                # 多值列表: env_name 包含多个可选值, 命中其中一个即可
                {"app_code": ["myapp"], "env_name": ["prod", "stag"]},
                {"application_code": "myapp", "module_name": "default", "env_name": "stag"},
                True,
                id="multi_value_env_match",
            ),
            pytest.param(
                # 不匹配: app_code 不同, 应回退到 FIFO
                {"app_code": ["otherapp"], "module_name": ["default"], "env_name": ["prod"]},
                {"application_code": "myapp", "module_name": "default", "env_name": "prod"},
                False,
                id="app_code_mismatch_fallback_fifo",
            ),
            pytest.param(
                # 不匹配: 策略绑定了 env_name 但 params 提供的 env 不在列表中
                {"app_code": ["myapp"], "env_name": ["prod"]},
                {"application_code": "myapp", "module_name": "default", "env_name": "stag"},
                False,
                id="env_mismatch_fallback_fifo",
            ),
        ],
    )
    def test_provision_with_policy_match(self, bk_service, bk_plan, policy_binding, params, expect_policy):
        """根据不同的 binding_policy 与 params 组合, 验证策略匹配或回退到 FIFO"""
        fifo_ins = G(
            PreCreatedInstance,
            plan=bk_plan,
            allocation_type=PreCreatedInstanceAllocationType.FIFO,
            credentials=json.dumps({"host": "fifo-host"}),
        )
        policy_ins = G(
            PreCreatedInstance,
            plan=bk_plan,
            allocation_type=PreCreatedInstanceAllocationType.POLICY,
            credentials=json.dumps({"host": "policy-host"}),
            binding_policy=policy_binding,
        )

        instance = bk_service.create_service_instance_by_plan(bk_plan, params)

        if expect_policy:
            assert instance.config["__pk__"] == str(policy_ins.pk)
            assert json.loads(instance.credentials)["REDIS_HOST"] == "policy-host"
            assert PreCreatedInstance.objects.get(pk=policy_ins.pk).is_allocated
            assert not PreCreatedInstance.objects.get(pk=fifo_ins.pk).is_allocated
        else:
            assert instance.config["__pk__"] == str(fifo_ins.pk)
            assert json.loads(instance.credentials)["REDIS_HOST"] == "fifo-host"
            assert PreCreatedInstance.objects.get(pk=fifo_ins.pk).is_allocated
            assert not PreCreatedInstance.objects.get(pk=policy_ins.pk).is_allocated

    def test_provision_policy_score_priority(self, bk_service, bk_plan):
        """多个 POLICY 实例均匹配时, 应选中得分最高的 (app_code=3 > module_name=2 > env_name=1)"""
        G(
            PreCreatedInstance,
            plan=bk_plan,
            allocation_type=PreCreatedInstanceAllocationType.FIFO,
            credentials=json.dumps({"host": "fifo-host"}),
        )
        # 只匹配 env_name, score=1
        low_score_ins = G(
            PreCreatedInstance,
            plan=bk_plan,
            allocation_type=PreCreatedInstanceAllocationType.POLICY,
            credentials=json.dumps({"host": "low-score"}),
            binding_policy={"env_name": ["prod"]},
        )
        # 匹配 app_code + module_name, score=3+2=5
        high_score_ins = G(
            PreCreatedInstance,
            plan=bk_plan,
            allocation_type=PreCreatedInstanceAllocationType.POLICY,
            credentials=json.dumps({"host": "high-score"}),
            binding_policy={"app_code": ["myapp"], "module_name": ["default"]},
        )

        params = {"application_code": "myapp", "module_name": "default", "env_name": "prod"}
        instance = bk_service.create_service_instance_by_plan(bk_plan, params)

        assert instance.config["__pk__"] == str(high_score_ins.pk)
        assert json.loads(instance.credentials)["REDIS_HOST"] == "high-score"
        assert PreCreatedInstance.objects.get(pk=high_score_ins.pk).is_allocated
        assert not PreCreatedInstance.objects.get(pk=low_score_ins.pk).is_allocated

    def test_provision_raises_when_all_allocated(self, bk_service, bk_plan):
        """所有实例均已分配时, 应抛出 ResourceNotEnoughError"""
        G(PreCreatedInstance, plan=bk_plan, credentials=json.dumps({}), is_allocated=True)

        with pytest.raises(InsufficientResourceError, match="资源不足"):
            bk_service.create_service_instance_by_plan(bk_plan, {})
