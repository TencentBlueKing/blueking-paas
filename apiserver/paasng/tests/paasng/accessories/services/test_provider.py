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
from paasng.accessories.services.exceptions import ResourceNotEnoughError
from paasng.accessories.services.models import Plan, PreCreatedInstance, PreCreatedInstanceBindingPolicy

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

    def test_provision_with_policy_match(self, bk_service, bk_plan):
        """带完整 params 时, 应通过策略匹配选中 POLICY 实例而非 FIFO 实例"""
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
        )
        G(
            PreCreatedInstanceBindingPolicy,
            pre_created_instance=policy_ins,
            app_code="myapp",
            module_name="default",
            env_name="prod",
        )

        params = {"application_code": "myapp", "module_name": "default", "env_name": "prod"}
        instance = bk_service.create_service_instance_by_plan(bk_plan, params)

        assert instance.config["__pk__"] == str(policy_ins.pk)
        assert json.loads(instance.credentials)["REDIS_HOST"] == "policy-host"
        assert PreCreatedInstance.objects.get(pk=policy_ins.pk).is_allocated
        assert not PreCreatedInstance.objects.get(pk=fifo_ins.pk).is_allocated

    def test_provision_raises_when_all_allocated(self, bk_service, bk_plan):
        """所有实例均已分配时, 应抛出 ResourceNotEnoughError"""
        G(PreCreatedInstance, plan=bk_plan, credentials=json.dumps({}), is_allocated=True)

        with pytest.raises(ResourceNotEnoughError, match="资源不足"):
            bk_service.create_service_instance_by_plan(bk_plan, {})


class TestPreCreatedInstanceBindingPolicy:
    def test_resolve_policy_match_priority(self, bk_plan):
        ins_app_env = G(PreCreatedInstance, plan=bk_plan, allocation_type=PreCreatedInstanceAllocationType.POLICY)
        ins_module_env = G(PreCreatedInstance, plan=bk_plan, allocation_type=PreCreatedInstanceAllocationType.POLICY)
        ins_env_only = G(PreCreatedInstance, plan=bk_plan, allocation_type=PreCreatedInstanceAllocationType.POLICY)

        policy_app_env = G(
            PreCreatedInstanceBindingPolicy,
            pre_created_instance=ins_app_env,
            app_code="app",
            module_name=None,
            env_name="prod",
        )
        policy_module_env = G(
            PreCreatedInstanceBindingPolicy,
            pre_created_instance=ins_module_env,
            app_code=None,
            module_name="mod",
            env_name="prod",
        )
        policy_env_only = G(
            PreCreatedInstanceBindingPolicy,
            pre_created_instance=ins_env_only,
            app_code=None,
            module_name=None,
            env_name="prod",
        )

        # 优先级计算可以认为是比较 (app_code, module_name, env) 的大小, app_code 优先
        qs = PreCreatedInstanceBindingPolicy.objects.filter(
            pre_created_instance__in=PreCreatedInstance.objects.filter(plan=bk_plan)
        )
        policy = PreCreatedInstanceBindingPolicy.objects.resolve_policy("app", "mod", "prod", qs)
        assert policy == policy_app_env

        policy = PreCreatedInstanceBindingPolicy.objects.resolve_policy("other", "mod", "prod", qs)
        assert policy == policy_module_env

        policy = PreCreatedInstanceBindingPolicy.objects.resolve_policy(None, None, "prod", qs)
        assert policy == policy_env_only


class TestPreCreatedInstanceSelectForRequest:
    def test_missing_params_uses_fifo_without_policies(self, bk_plan):
        ins_with_policy = G(PreCreatedInstance, plan=bk_plan, allocation_type=PreCreatedInstanceAllocationType.POLICY)
        ins_without_policy = G(PreCreatedInstance, plan=bk_plan, allocation_type=PreCreatedInstanceAllocationType.FIFO)
        G(PreCreatedInstanceBindingPolicy, pre_created_instance=ins_with_policy, app_code="app")

        instance = PreCreatedInstance.objects.select_by_policy_or_fifo(bk_plan, {})
        assert instance == ins_without_policy

    @pytest.mark.parametrize(
        ("policy_env", "expect_policy"),
        [("prod", True), ("stag", False)],
    )
    def test_policy_match_and_fallback(self, bk_plan, policy_env, expect_policy):
        fifo_first = G(PreCreatedInstance, plan=bk_plan, allocation_type=PreCreatedInstanceAllocationType.FIFO)
        policy_instance = G(PreCreatedInstance, plan=bk_plan, allocation_type=PreCreatedInstanceAllocationType.POLICY)
        G(
            PreCreatedInstanceBindingPolicy,
            pre_created_instance=policy_instance,
            app_code="app",
            module_name="mod",
            env_name=policy_env,
        )

        instance = PreCreatedInstance.objects.select_by_policy_or_fifo(
            bk_plan, {"application_code": "app", "module_name": "mod", "env_name": "prod"}
        )
        assert instance == (policy_instance if expect_policy else fifo_first)

    @pytest.mark.parametrize(
        ("params", "description"),
        [
            ({}, "FIFO path"),
            ({"application_code": "app", "module_name": "", "env_name": "prod"}, "POLICY path"),
        ],
    )
    def test_all_allocated_returns_none(self, bk_plan, params, description):
        """FIFO 和 POLICY 两条路径下, 所有实例已分配时应返回 None"""
        G(PreCreatedInstance, plan=bk_plan, allocation_type=PreCreatedInstanceAllocationType.FIFO, is_allocated=True)
        policy_ins = G(
            PreCreatedInstance,
            plan=bk_plan,
            allocation_type=PreCreatedInstanceAllocationType.POLICY,
            is_allocated=True,
        )
        G(PreCreatedInstanceBindingPolicy, pre_created_instance=policy_ins, app_code="app", env_name="prod")

        assert PreCreatedInstance.objects.select_by_policy_or_fifo(bk_plan, params) is None
