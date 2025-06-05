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
from django_dynamic_fixture import G

from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.binding_policy.policy import ServiceBindingPrecedencePolicyDTO
from paasng.accessories.servicehub.binding_policy.selector import (
    PlanSelector,
    PossiblePlansResultType,
    get_plan_by_env,
)
from paasng.accessories.servicehub.constants import PrecedencePolicyCondType
from paasng.accessories.servicehub.exceptions import MultiplePlanFoundError, NoPlanFoundError
from paasng.accessories.servicehub.manager import mixed_plan_mgr, mixed_service_mgr
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.engine.constants import AppEnvName
from tests.api.test_cnative_migration import get_random_string
from tests.paasng.accessories.servicehub import data_mocks

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.xdist_group(name="remote-services"),
]


# Only test remote service object, no need to test local because servicehub/test_manager.py::TestMixedMgrBindService
# already covered the local service object.
@pytest.fixture()
@pytest.mark.usefixture("_faked_remote_services")
def service_obj(_faked_remote_services):
    return mixed_service_mgr.get(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"])


@pytest.fixture
def plan1(service_obj):
    return list(mixed_plan_mgr.list(service_obj))[0]


@pytest.fixture
def plan2(service_obj):
    return list(mixed_plan_mgr.list(service_obj))[1]


class TestPlanSelectorSelect:
    def test_static(self, service_obj, bk_prod_env, plan1):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid])

        assert PlanSelector().select(service_obj, bk_prod_env) == plan1

    def test_env_specified(self, service_obj, bk_stag_env, bk_prod_env, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(
            env_plans={AppEnvName.STAG: [plan1.uuid], AppEnvName.PROD: [plan2.uuid]},
        )
        assert PlanSelector().select(service_obj, bk_stag_env) == plan1
        assert PlanSelector().select(service_obj, bk_prod_env) == plan2

    def test_not_found(self, service_obj, bk_prod_env):
        with pytest.raises(NoPlanFoundError):
            PlanSelector().select(service_obj, bk_prod_env)

    def test_multiple_found(self, service_obj, bk_prod_env, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid, plan2.uuid])

        with pytest.raises(MultiplePlanFoundError):
            PlanSelector().select(service_obj, bk_prod_env)


class TestPlanSelectorSelectWithPrecedenceRegionIn:
    @pytest.fixture
    def with_region1(self, bk_app):
        bk_app.region = "r1"
        bk_app.save(update_fields=["region"])

    @pytest.fixture
    def with_region2(self, bk_app):
        bk_app.region = "r2"
        bk_app.save(update_fields=["region"])

    def test_static_with_region_in_matches(self, service_obj, bk_prod_env, plan1, plan2, with_region1):
        self._setup_static_precedence_policies(service_obj, plan1, plan2)
        selected_plan = PlanSelector().select(service_obj, bk_prod_env)
        assert selected_plan == plan2

    def test_static_with_region_in_not_match(self, service_obj, bk_prod_env, plan1, plan2, with_region2):
        self._setup_static_precedence_policies(service_obj, plan1, plan2)
        selected_plan = PlanSelector().select(service_obj, bk_prod_env)
        assert selected_plan == plan1

    def test_env_specific_with_region_in_matches(
        self, service_obj, bk_stag_env, bk_prod_env, plan1, plan2, with_region1
    ):
        self._setup_env_specific_precedence_policies(service_obj, plan1, plan2)
        assert PlanSelector().select(service_obj, bk_stag_env) == plan2
        assert PlanSelector().select(service_obj, bk_prod_env) == plan1

    def _setup_static_precedence_policies(self, service_obj, plan1, plan2):
        """setup precedence policies for testing

        - region: r1 -> plan2
        - * -> plan1
        """
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_rule_based(
            [
                ServiceBindingPrecedencePolicyDTO(
                    cond_type=PrecedencePolicyCondType.REGION_IN,
                    cond_data={"regions": ["r1"]},
                    plans=[plan2.uuid],
                    priority=1,
                ),
                ServiceBindingPrecedencePolicyDTO(
                    cond_type=PrecedencePolicyCondType.ALWAYS_MATCH,
                    cond_data={},
                    plans=[plan1.uuid],
                    priority=0,
                ),
            ]
        )
        return plan1, plan2

    def _setup_env_specific_precedence_policies(self, service_obj, plan1, plan2):
        """setup precedence policies for testing

        - region: r1 -> {stag: plan2, prod: plan1}
        """
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_rule_based(
            [
                ServiceBindingPrecedencePolicyDTO(
                    cond_type=PrecedencePolicyCondType.REGION_IN,
                    cond_data={"regions": ["r1"]},
                    env_plans={AppEnvName.STAG: [plan2.uuid], AppEnvName.PROD: [plan1.uuid]},
                    priority=1,
                ),
                ServiceBindingPrecedencePolicyDTO(
                    cond_type=PrecedencePolicyCondType.ALWAYS_MATCH,
                    cond_data={},
                    plans=[plan1.uuid],
                    priority=0,
                ),
            ]
        )


@pytest.mark.usefixtures("_with_wl_apps")
class TestPlanSelectorSelectWithPrecedenceClusterIn:
    @pytest.fixture()
    def random_cluster(self, bk_app):
        cluster_name = get_random_string(6)
        return G(Cluster, name=cluster_name)

    def test_static_with_cluster_in_matches(self, service_obj, bk_prod_env, plan1, plan2):
        cluster_name = EnvClusterService(bk_prod_env).get_cluster_name()
        self._setup_static_precedence_policies(service_obj, cluster_name, plan1, plan2)
        assert PlanSelector().select(service_obj, bk_prod_env) == plan2

    def test_static_with_cluster_in_not_matches(self, service_obj, bk_prod_env, random_cluster, plan1, plan2):
        cluster_name = EnvClusterService(bk_prod_env).get_cluster_name()
        self._setup_static_precedence_policies(service_obj, cluster_name, plan1, plan2)

        # Switch to another cluster
        EnvClusterService(bk_prod_env).bind_cluster(random_cluster.name)

        assert PlanSelector().select(service_obj, bk_prod_env) == plan1

    def _setup_static_precedence_policies(self, service_obj, cluster_name, plan1, plan2):
        """setup precedence policies for testing

        - region: r1 -> plan2
        - * -> plan1
        """
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_rule_based(
            [
                ServiceBindingPrecedencePolicyDTO(
                    cond_type=PrecedencePolicyCondType.CLUSTER_IN,
                    cond_data={"cluster_names": [cluster_name]},
                    plans=[plan2.uuid],
                    priority=1,
                ),
                ServiceBindingPrecedencePolicyDTO(
                    cond_type=PrecedencePolicyCondType.ALWAYS_MATCH,
                    cond_data={},
                    plans=[plan1.uuid],
                    priority=0,
                ),
            ]
        )


class TestPlanSelectorListPossiblePlans:
    def test_static_single(self, service_obj, bk_module, bk_prod_env, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid])
        possible_plans = PlanSelector().list_possible_plans(service_obj, bk_module)

        assert possible_plans.has_multiple_plans() is False
        assert possible_plans.get_result_type() == PossiblePlansResultType.STATIC
        assert possible_plans.get_static_plans() == [plan1]
        assert possible_plans.get_env_specific_plans() is None

    def test_static_multiple(self, service_obj, bk_module, bk_prod_env, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid, plan2.uuid])
        possible_plans = PlanSelector().list_possible_plans(service_obj, bk_module)

        assert possible_plans.has_multiple_plans() is True
        assert possible_plans.get_result_type() == PossiblePlansResultType.STATIC
        assert possible_plans.get_static_plans() == [plan1, plan2]
        assert possible_plans.get_env_specific_plans() is None

    def test_env_specific_single(self, service_obj, bk_module, bk_prod_env, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(
            env_plans={AppEnvName.STAG: [plan1.uuid], AppEnvName.PROD: [plan2.uuid]},
        )
        possible_plans = PlanSelector().list_possible_plans(service_obj, bk_module)

        assert possible_plans.has_multiple_plans() is False
        assert possible_plans.get_result_type() == PossiblePlansResultType.ENV_SPECIFIC
        assert possible_plans.get_static_plans() is None
        assert possible_plans.get_env_specific_plans() == {
            "stag": [plan1],
            "prod": [plan2],
        }

    def test_env_specific_has_multi(self, service_obj, bk_module, bk_prod_env, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(
            env_plans={AppEnvName.STAG: [plan1.uuid], AppEnvName.PROD: [plan1.uuid, plan2.uuid]},
        )
        possible_plans = PlanSelector().list_possible_plans(service_obj, bk_module)

        assert possible_plans.has_multiple_plans() is True
        assert possible_plans.get_result_type() == PossiblePlansResultType.ENV_SPECIFIC
        assert possible_plans.get_static_plans() is None
        assert possible_plans.get_env_specific_plans() == {
            "stag": [plan1],
            "prod": [plan1, plan2],
        }

    def test_tenant_isolation(self, service_obj, bk_module, bk_prod_env, plan1, plan2, tenant_id):
        # 配置租户为 'system' 的 ServiceBindingPolicy
        SvcBindingPolicyManager(service_obj, tenant_id).set_uniform(plans=[plan1.uuid, plan2.uuid])

        possible_plans = PlanSelector().list_possible_plans(service_obj, bk_module)
        assert possible_plans.get_static_plans() == []


class Test__get_plan_by_env:
    @pytest.fixture
    def with_plans_env(self, service_obj, bk_module, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(
            env_plans={AppEnvName.STAG: [plan1.uuid], AppEnvName.PROD: [plan1.uuid, plan2.uuid]},
        )

    @pytest.fixture
    def with_plans_static(self, service_obj, bk_module, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid])

    def test_select_success(self, service_obj, bk_stag_env, plan1, with_plans_static):
        selected_plan = get_plan_by_env(service_obj, bk_stag_env, None, None)
        assert selected_plan == plan1

    def test_select_fail(self, service_obj, bk_stag_env):
        with pytest.raises(ValueError, match="no plans found"):
            get_plan_by_env(service_obj, bk_stag_env, None, None)

    def test_given_plan_id_static_ok(self, service_obj, bk_stag_env, plan1, with_plans_static):
        selected_plan = get_plan_by_env(service_obj, bk_stag_env, plan1.uuid, None)
        assert selected_plan == plan1

    def test_given_plan_id_static_fail(self, service_obj, bk_stag_env, plan2, with_plans_static):
        with pytest.raises(ValueError, match="no plan found by given plan_id"):
            get_plan_by_env(service_obj, bk_stag_env, plan2.uuid, None)

    def test_given_env_map_ok(self, service_obj, bk_stag_env, plan1, plan2, with_plans_env):
        env_plan_id_map = {"stag": plan1.uuid}
        selected_plan = get_plan_by_env(service_obj, bk_stag_env, None, env_plan_id_map)
        assert selected_plan == plan1

    def test_given_env_map_fail(self, service_obj, bk_stag_env, plan2, with_plans_env):
        env_plan_id_map = {"stag": plan2.uuid}
        with pytest.raises(ValueError, match="no plan found by given plan_id"):
            get_plan_by_env(service_obj, bk_stag_env, None, env_plan_id_map)
