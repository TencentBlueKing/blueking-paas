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
from paasng.accessories.servicehub.binding_policy.manager import ServiceBindingPolicyManager
from paasng.accessories.servicehub.binding_policy.selector import PlanSelector, PossiblePlansResultType
from paasng.accessories.servicehub.constants import PrecedencePolicyCondType
from paasng.accessories.servicehub.exceptions import MultiplePlanFoundError, NoPlanFoundError
from paasng.accessories.servicehub.manager import mixed_plan_mgr, mixed_service_mgr
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.platform.engine.constants import AppEnvName
from tests.api.test_cnative_migration import get_random_string
from tests.paasng.accessories.servicehub import data_mocks
from tests.utils.helpers import generate_random_string

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.xdist_group(name="remote-services"),
]


# The default region value
region = "r1"


@pytest.fixture()
def local_service():
    service = G(Service, name="mysql", category=G(ServiceCategory), region=region, logo_b64="dummy")
    # Create some plans
    G(Plan, name=generate_random_string(), service=service)
    G(Plan, name=generate_random_string(), service=service)
    return mixed_service_mgr.get(service.uuid, region=region)


@pytest.fixture()
@pytest.mark.usefixture("_faked_remote_services")
def remote_service(_faked_remote_services):
    return mixed_service_mgr.get(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"], region=region)


@pytest.fixture(params=["local", "remote"])
def service_obj(request, local_service, remote_service):
    """Service object for testing, this fixture will yield both a remote and a local service"""
    if request.param == "remote":
        return request.getfixturevalue("remote_service")
    elif request.param in "local":
        return request.getfixturevalue("local_service")
    else:
        raise ValueError("Invalid type_ parameter")


@pytest.fixture
def plan1(service_obj):
    return list(mixed_plan_mgr.list(service_obj))[0]


@pytest.fixture
def plan2(service_obj):
    return list(mixed_plan_mgr.list(service_obj))[1]


class TestPlanSelectorSelect:
    def test_static(self, service_obj, bk_prod_env, plan1):
        ServiceBindingPolicyManager(service_obj).set_static([plan1])

        assert PlanSelector().select(service_obj, bk_prod_env) == plan1

    def test_env_specified(self, service_obj, bk_stag_env, bk_prod_env, plan1, plan2):
        ServiceBindingPolicyManager(service_obj).set_env_specific(
            env_plans=[
                (AppEnvName.STAG, [plan1]),
                (AppEnvName.PROD, [plan2]),
            ]
        )

        assert PlanSelector().select(service_obj, bk_stag_env) == plan1
        assert PlanSelector().select(service_obj, bk_prod_env) == plan2

    def test_not_found(self, service_obj, bk_prod_env):
        with pytest.raises(NoPlanFoundError):
            PlanSelector().select(service_obj, bk_prod_env)

    def test_multiple_found(self, service_obj, bk_prod_env, plan1, plan2):
        ServiceBindingPolicyManager(service_obj).set_static([plan1, plan2])

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
        ServiceBindingPolicyManager(service_obj).set_static([plan1])
        ServiceBindingPolicyManager(service_obj).add_precedence_static(
            cond_type=PrecedencePolicyCondType.REGION_IN, cond_data={"regions": ["r1"]}, plans=[plan2]
        )
        return plan1, plan2

    def _setup_env_specific_precedence_policies(self, service_obj, plan1, plan2):
        """setup precedence policies for testing

        - region: r1 -> {stag: plan2, prod: plan1}
        """
        ServiceBindingPolicyManager(service_obj).add_precedence_env_specific(
            cond_type=PrecedencePolicyCondType.REGION_IN,
            cond_data={"regions": ["r1"]},
            env_plans=[(AppEnvName.STAG, [plan2]), (AppEnvName.PROD, [plan1])],
        )


@pytest.mark.usefixtures("_with_wl_apps")
class TestPlanSelectorSelectWithPrecedenceClusterIn:
    @pytest.fixture()
    def random_cluster(self, bk_app):
        cluster_name = get_random_string(6)
        return G(Cluster, name=cluster_name, region=bk_app.region)

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
        ServiceBindingPolicyManager(service_obj).set_static([plan1])
        ServiceBindingPolicyManager(service_obj).add_precedence_static(
            cond_type=PrecedencePolicyCondType.CLUSTER_IN, cond_data={"cluster_names": [cluster_name]}, plans=[plan2]
        )


class TestPlanSelectorListPossiblePlans:
    def test_static_single(self, service_obj, bk_module, bk_prod_env, plan1, plan2):
        ServiceBindingPolicyManager(service_obj).set_static([plan1])
        possible_plans = PlanSelector().list_possible_plans(service_obj, bk_module)

        assert possible_plans.has_multiple_plans() is False
        assert possible_plans.get_result_type() == PossiblePlansResultType.STATIC
        assert possible_plans.get_static_plans() == [plan1]
        assert possible_plans.get_env_specific_plans() is None

    def test_static_multiple(self, service_obj, bk_module, bk_prod_env, plan1, plan2):
        ServiceBindingPolicyManager(service_obj).set_static([plan1, plan2])
        possible_plans = PlanSelector().list_possible_plans(service_obj, bk_module)

        assert possible_plans.has_multiple_plans() is True
        assert possible_plans.get_result_type() == PossiblePlansResultType.STATIC
        assert possible_plans.get_static_plans() == [plan1, plan2]
        assert possible_plans.get_env_specific_plans() is None

    def test_env_specific_single(self, service_obj, bk_module, bk_prod_env, plan1, plan2):
        ServiceBindingPolicyManager(service_obj).set_env_specific(
            env_plans=[
                (AppEnvName.STAG, [plan1]),
                (AppEnvName.PROD, [plan2]),
            ]
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
        ServiceBindingPolicyManager(service_obj).set_env_specific(
            env_plans=[
                (AppEnvName.STAG, [plan1]),
                (AppEnvName.PROD, [plan1, plan2]),
            ]
        )
        possible_plans = PlanSelector().list_possible_plans(service_obj, bk_module)

        assert possible_plans.has_multiple_plans() is True
        assert possible_plans.get_result_type() == PossiblePlansResultType.ENV_SPECIFIC
        assert possible_plans.get_static_plans() is None
        assert possible_plans.get_env_specific_plans() == {
            "stag": [plan1],
            "prod": [plan1, plan2],
        }
