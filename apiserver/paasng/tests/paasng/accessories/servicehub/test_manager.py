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

import datetime
import uuid
from json import dumps
from typing import Dict
from unittest import mock
from uuid import UUID

import pytest
from django_dynamic_fixture import G

from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.binding_policy.policy import (
    PolicyCombinationConfig,
    ServiceBindingPolicyDTO,
    ServiceBindingPrecedencePolicyDTO,
)
from paasng.accessories.servicehub.constants import Category, PrecedencePolicyCondType, ServiceAllocationPolicyType
from paasng.accessories.servicehub.exceptions import (
    BindServicePlanError,
    ServiceObjNotFound,
    UnboundSvcAttachmentDoesNotExist,
)
from paasng.accessories.servicehub.local import LocalServiceMgr, LocalServiceObj
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import ServiceEngineAppAttachment
from paasng.accessories.servicehub.remote import RemoteServiceObj
from paasng.accessories.servicehub.services import ServiceInstanceObj
from paasng.accessories.services.models import Plan, Service, ServiceCategory, ServiceInstance
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.modules.manager import ModuleCleaner
from tests.paasng.accessories.servicehub import data_mocks

pytestmark = [pytest.mark.django_db, pytest.mark.xdist_group(name="remote-services")]


@pytest.mark.usefixtures("_faked_remote_services")
class TestMixedMgrGetAndList:
    def test_list_by_category(self):
        services = list(mixed_service_mgr.list_by_category(category_id=Category.DATA_STORAGE))
        assert len(services) == 1

        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        G(Service, category=category, logo_b64="dummy")

        services = list(mixed_service_mgr.list_by_category(category_id=Category.DATA_STORAGE))
        assert len(services) == 2

    def test_list(self):
        # 2 remote services
        assert len(list(mixed_service_mgr.list_visible())) == 2

        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        G(Service, category=category, logo_b64="dummy")

        assert len(list(mixed_service_mgr.list_visible())) == 3

    def test_get_remote_found(self):
        obj = mixed_service_mgr.get(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"])
        assert obj is not None

    def test_get_local_found(self):
        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        svc = G(Service, category=category, logo_b64="dummy")

        obj = mixed_service_mgr.get(str(svc.uuid))
        assert obj is not None

    def test_get_not_found(self):
        with pytest.raises(ServiceObjNotFound):
            mixed_service_mgr.get(uuid="f" * 64)

    def test_find_by_name_local_found(self):
        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        svc = G(Service, category=category, logo_b64="dummy")

        obj = mixed_service_mgr.find_by_name(str(svc.name))
        assert obj is not None
        assert isinstance(obj, LocalServiceObj)
        assert not isinstance(obj, RemoteServiceObj)

    def test_find_by_name_remote_found(self):
        obj = mixed_service_mgr.find_by_name(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["name"])
        assert obj is not None
        assert not isinstance(obj, LocalServiceObj)
        assert isinstance(obj, RemoteServiceObj)

    def test_find_by_name_not_found(self):
        with pytest.raises(ServiceObjNotFound):
            mixed_service_mgr.find_by_name("non-exists-name")

    @mock.patch("paasng.accessories.servicehub.manager.MixedServiceMgr.list_provisioned_rels")
    def test_get_env_vars_ordering(self, mock_list_provisioned_rels):
        def create_mock_rel(create_time: "datetime.datetime", **credentials):
            rel = mock.MagicMock()
            rel.get_instance.return_value = ServiceInstanceObj(
                uuid="",
                credentials=credentials,
                config={},
                create_time=create_time,
                tenant_id=DEFAULT_TENANT_ID,
            )
            return rel

        mock_list_provisioned_rels.return_value = [
            create_mock_rel(datetime.datetime(2020, 1, 3), c=3),
            create_mock_rel(datetime.datetime(2020, 1, 1), a=1, b=1),
            create_mock_rel(datetime.datetime(2020, 1, 2), b=2, c=2),
        ]

        envs = mixed_service_mgr.get_env_vars(mock.MagicMock())
        assert envs == {"a": 1, "b": 2, "c": 3}


class TestMixedMgrBindService:
    """All test cases in this class test both local and remote services by using
    the parametrized fixture `service_obj`."""

    def test_no_plans(self, bk_module, service_obj, plan1):
        with pytest.raises(BindServicePlanError):
            mixed_service_mgr.bind_service(service_obj, bk_module)

    def test_static_single(self, bk_module, service_obj, plan1):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid])
        rel_pk = mixed_service_mgr.bind_service(service_obj, bk_module)
        assert rel_pk is not None

    def test_static_multi(self, bk_module, service_obj, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid, plan2.uuid])
        with pytest.raises(BindServicePlanError):
            mixed_service_mgr.bind_service(service_obj, bk_module)

    def test_valid_plan_id(self, service_obj, bk_module, plan1):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid])
        rel_pk = mixed_service_mgr.bind_service(service_obj, bk_module, plan_id=plan1.uuid)
        assert rel_pk is not None

    def test_invalid_plan_id(self, service_obj, bk_module, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid])
        with pytest.raises(BindServicePlanError):
            mixed_service_mgr.bind_service(service_obj, bk_module, plan_id=plan2.uuid)

    def test_valid_env_plan_id_map(self, service_obj, bk_module, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(
            env_plans={"stag": [plan1.uuid], "prod": [plan2.uuid]}
        )
        rel_pk = mixed_service_mgr.bind_service(
            service_obj, bk_module, env_plan_id_map={"stag": plan1.uuid, "prod": plan2.uuid}
        )
        assert rel_pk is not None

    def test_invalid_env_plan_id_map(self, service_obj, bk_module, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(
            env_plans={"stag": [plan1.uuid], "prod": [plan1.uuid]},
        )
        with pytest.raises(BindServicePlanError):
            mixed_service_mgr.bind_service(
                service_obj, bk_module, env_plan_id_map={"stag": plan1.uuid, "prod": plan2.uuid}
            )

    # Tests for bind_use_first_plan start
    def test_use_first_plan_no_plans(self, bk_module, service_obj, plan1):
        with pytest.raises(BindServicePlanError):
            mixed_service_mgr.bind_service_use_first_plan(service_obj, bk_module)

    def test_use_first_plan_ok(self, bk_module, service_obj, bk_stag_env, plan1, plan2):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan2.uuid, plan1.uuid])
        rel_pk = mixed_service_mgr.bind_service_use_first_plan(service_obj, bk_module)
        assert rel_pk is not None

        # Check the bound plan
        rels = mixed_service_mgr.list_all_rels(bk_stag_env.engine_app, service_obj.uuid)
        assert all(rel.get_plan().name == plan2.name for rel in rels)

    # Tests for list_binded start

    def test_list_binded(self, service_obj, bk_app, bk_module, plan1):
        assert list(mixed_service_mgr.list_binded(bk_module)) == []
        for env in bk_app.envs.all():
            assert list(mixed_service_mgr.list_unprovisioned_rels(env.engine_app)) == []

        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[plan1.uuid])
        rel_pk = mixed_service_mgr.bind_service(service_obj, bk_module)

        assert rel_pk is not None
        assert list(mixed_service_mgr.list_binded(bk_module)) == [service_obj]
        for env in bk_app.envs.all():
            assert len(list(mixed_service_mgr.list_unprovisioned_rels(env.engine_app))) == 1


class TestSvcBindingPolicyManager:
    @pytest.fixture()
    def policy_config(self, bk_app, service_obj, plan1, plan2):
        """A pre-configured rule-based combination config object for testing."""
        allocation_precedence_policies = [
            ServiceBindingPrecedencePolicyDTO(
                cond_type=PrecedencePolicyCondType.REGION_IN,
                cond_data={"regions": [bk_app.region]},
                priority=2,
                plans=[plan1.uuid],
            ),
            ServiceBindingPrecedencePolicyDTO(
                cond_type=PrecedencePolicyCondType.CLUSTER_IN,
                cond_data={"cluster_name": ["cluster1", "cluster2"]},
                priority=1,
                env_plans={"stag": [plan2.uuid]},
            ),
            ServiceBindingPrecedencePolicyDTO(
                cond_type=PrecedencePolicyCondType.ALWAYS_MATCH,
                cond_data={},
                priority=0,
                env_plans={"stag": [plan1.uuid]},
            ),
        ]

        return PolicyCombinationConfig(
            tenant_id=DEFAULT_TENANT_ID,
            service_id=service_obj.uuid,
            policy_type=ServiceAllocationPolicyType.RULE_BASED,
            allocation_precedence_policies=allocation_precedence_policies,
        )

    @pytest.fixture()
    def uniform_policy_config(self, bk_app, service_obj, plan1):
        """A pre-configured uniform combination config object for testing."""
        return PolicyCombinationConfig(
            tenant_id=DEFAULT_TENANT_ID,
            service_id=service_obj.uuid,
            policy_type=ServiceAllocationPolicyType.UNIFORM,
            allocation_policy=ServiceBindingPolicyDTO(plans=[plan1.uuid]),
        )

    def test_create_with_invalid_cfg(self, service_obj, bk_app, bk_module, plan1, plan2):
        allocation_precedence_policies = [
            ServiceBindingPrecedencePolicyDTO(
                cond_type=PrecedencePolicyCondType.CLUSTER_IN,
                cond_data={"cluster_name": ["cluster1", "cluster2"]},
                priority=1,
                env_plans={"stag": [plan2.uuid]},
            ),
        ]

        cfg = PolicyCombinationConfig(
            tenant_id=DEFAULT_TENANT_ID,
            service_id=service_obj.uuid,
            policy_type=ServiceAllocationPolicyType.RULE_BASED,
            allocation_precedence_policies=allocation_precedence_policies,
        )
        mgr = SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID)
        with pytest.raises(ValueError, match=r"The policy with the minimum priority*"):
            mgr.save_comb_cfg(cfg)

    def test_should_fail_when_save_invalid_plan_id(self, service_obj, uniform_policy_config):
        mgr = SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID)
        # Set an invalid plan ID
        uniform_policy_config.allocation_policy.plans = [uuid.uuid4().hex]
        with pytest.raises(ValueError, match=r".*does not belong to service.*"):
            mgr.save_comb_cfg(uniform_policy_config)

    def test_save_comb_cfg(self, service_obj, bk_app, bk_module, plan1, plan2, policy_config):
        mgr = SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID)
        mgr.save_comb_cfg(policy_config)

        comb_cfg = mgr.get_comb_cfg()
        assert comb_cfg is not None
        assert comb_cfg.policy_type == ServiceAllocationPolicyType.RULE_BASED.value
        assert comb_cfg.allocation_policy is None
        policies = comb_cfg.allocation_precedence_policies
        assert policies is not None
        assert len(policies) == 3
        p1, p2, p3 = policies
        assert [
            (p1.cond_data, p1.plans, p1.priority),
            (p2.cond_data, p2.env_plans, p2.priority),
            (p3.cond_data, p3.env_plans, p3.priority),
        ] == [
            ({"regions": [bk_app.region]}, [plan1.uuid], 2),
            ({"cluster_name": ["cluster1", "cluster2"]}, {"stag": [plan2.uuid]}, 1),
            ({}, {"stag": [plan1.uuid]}, 0),
        ]

    def test_save_comb_cfg_multiple_times(self, service_obj, bk_app, bk_module, policy_config, uniform_policy_config):
        mgr = SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID)
        mgr.save_comb_cfg(policy_config)
        mgr.save_comb_cfg(uniform_policy_config)

        policy_combination_config = mgr.get_comb_cfg()
        assert policy_combination_config == uniform_policy_config

    def test_get_comb_cfg(self, service_obj, policy_config):
        mgr = SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID)
        mgr.save_comb_cfg(policy_config)

        policy_combination_config = mgr.get_comb_cfg()
        assert policy_combination_config == policy_config

    def test_clean(self, service_obj, policy_config):
        mgr = SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID)
        mgr.save_comb_cfg(policy_config)

        mgr.clean()
        cfg = mgr.get_comb_cfg()
        assert cfg is None


class TestLocalMgrProvisionAndInstance:
    @pytest.fixture()
    def svc(self, bk_app):
        """Create a local service object."""
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        svc = G(Service, name="mysql", category=category, logo_b64="dummy")
        # Create 2 plans
        G(Plan, name="plan-stag", service=svc, config="{}")
        G(Plan, name="plan-prod", service=svc, config="{}")
        return svc

    @pytest.fixture()
    def service(self, svc, bk_module) -> LocalServiceObj:
        return LocalServiceMgr().get(svc.uuid)

    @pytest.fixture()
    def plan_stag(self, service):
        plans = service.get_plans()
        return next((p for p in plans if p.name == "plan-stag"), None)

    @pytest.fixture(autouse=True)
    def _with_static_binding_policy(self, service, plan_stag):
        """Set the binding policy for the service to a static plan, so the binding can
        proceed by default.
        """
        SvcBindingPolicyManager(service, DEFAULT_TENANT_ID).set_uniform(plans=[plan_stag.uuid])

    @pytest.fixture()
    def instance_factory(self, svc, plan_stag):
        """A factory method that creates an instance object."""

        def _create():
            return G(
                ServiceInstance,
                service=svc,
                plan=plan_stag.db_object,
                config="{}",
                credentials=dumps({"MYSQL_USERNAME": "foo", "MYSQL_PASSWORD": "bar"}),
            )

        return _create

    @mock.patch("paasng.accessories.services.models.Service.create_service_instance_by_plan")
    def test_provision(self, mocked_method, instance_factory, svc, bk_app, bk_module):
        """Test service instance provision"""
        mocked_method.side_effect = [instance_factory(), instance_factory()]

        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        mgr.bind_service(service, bk_module)
        for env in bk_app.envs.all():
            for rel in mgr.list_unprovisioned_rels(env.engine_app):
                assert rel.is_provisioned() is False
                rel.provision()
                assert rel.is_provisioned() is True

    @mock.patch("paasng.accessories.services.models.Service.create_service_instance_by_plan")
    def test_instance_has_create_time_attr(self, mocked_method, instance_factory, svc, bk_app, bk_module):
        mocked_method.side_effect = [instance_factory()]
        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        mgr.bind_service(service, bk_module)
        env = bk_app.envs.first()
        for rel in mgr.list_unprovisioned_rels(env.engine_app):
            rel.provision()
            instance = rel.get_instance()
            assert isinstance(instance.create_time, datetime.datetime)

    @mock.patch("paasng.accessories.servicehub.constants.SERVICE_SENSITIVE_FIELDS", {"mysql": ["MYSQL_PASSWORD"]})
    @mock.patch("paasng.accessories.services.models.Service.create_service_instance_by_plan")
    def test_get_instance(self, mocked_method, instance_factory, svc, bk_app, bk_module):
        mocked_method.side_effect = [instance_factory(), instance_factory()]
        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        mgr.bind_service(service, bk_module)
        for env in bk_app.envs.all():
            for rel in mgr.list_unprovisioned_rels(env.engine_app):
                rel.provision()
                instance = rel.get_instance()

                assert len(instance.credentials) == 2
                assert instance.credentials["MYSQL_PASSWORD"] == "bar"

                assert len(instance.credentials_insensitive) == 1
                assert instance.credentials_insensitive["MYSQL_USERNAME"] == "foo"

                assert instance.get_hidden_credentials() == {}
                assert instance.should_remove_fields == ["MYSQL_PASSWORD"]
            break

    def test_module_is_bound_with(self, svc, bk_module):
        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        assert mgr.module_is_bound_with(service, bk_module) is False

        mgr.bind_service(service, bk_module)
        assert mgr.module_is_bound_with(service, bk_module) is True

    def test_get_attachment_by_instance_id(self, bk_module):
        expect_obj: Dict[UUID, ServiceEngineAppAttachment] = {}

        mgr = LocalServiceMgr()
        svc = mgr.find_by_name(name="mysql")

        # 绑定服务并创建服务实例
        mgr.bind_service(svc, bk_module)
        for env in bk_module.envs.all():
            for rel in mixed_service_mgr.list_unprovisioned_rels(env.engine_app, svc):
                plan = rel.get_plan()
                if plan.is_eager:
                    rel.provision()
                    expect_obj[rel.db_obj.service_instance_id] = rel.db_obj

        for _id, expected_val in expect_obj.values():
            assert mgr.get_attachment_by_instance_id(svc, _id) == expected_val

    @mock.patch("paasng.accessories.services.models.Service.delete_service_instance")
    @mock.patch("paasng.accessories.services.models.Service.create_service_instance_by_plan")
    def test_list_unbound_instance_rels(
        self, create_service_instance_by_plan, delete_service_instance, instance_factory, svc, bk_app, bk_module
    ):
        create_service_instance_by_plan.side_effect = [instance_factory(), instance_factory()]
        delete_service_instance.side_effect = (
            lambda service_instance: service_instance.delete() if service_instance else None
        )

        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        mgr.bind_service(service, bk_module)

        attachments: Dict[UUID, ServiceEngineAppAttachment] = {}
        for env in bk_app.envs.all():
            for rel in mgr.list_unprovisioned_rels(env.engine_app):
                rel.provision()
                attachments[rel.db_obj.service_instance_id] = rel.db_obj

        assert len(attachments) == 2

        cleaner = ModuleCleaner(bk_module)
        cleaner.delete_services(svc.uuid)

        unbound_rels = []
        for env in bk_app.envs.all():
            for u_rel in mgr.list_unbound_instance_rels(env.engine_app):
                assert u_rel.db_obj.service_instance_id in attachments
                assert u_rel.db_obj.service_id == attachments[u_rel.db_obj.service_instance_id].service_id
                assert u_rel.db_obj.engine_app == attachments[u_rel.db_obj.service_instance_id].engine_app
                unbound_rels.append(u_rel)

        assert len(unbound_rels) == len(attachments)

        for u_rel in unbound_rels:
            u_rel.recycle_resource()

        for env in bk_app.envs.all():
            for _rel in mgr.list_unbound_instance_rels(env.engine_app):
                pytest.fail("Expect no return unbound instance rels after recycle resource")

    @mock.patch("paasng.accessories.services.models.Service.delete_service_instance")
    @mock.patch("paasng.accessories.services.models.Service.create_service_instance_by_plan")
    def test_get_unbound_instance_rel_by_instance_id(
        self, create_service_instance_by_plan, delete_service_instance, instance_factory, svc, bk_app, bk_module
    ):
        create_service_instance_by_plan.side_effect = [instance_factory(), instance_factory()]
        delete_service_instance.side_effect = (
            lambda service_instance: service_instance.delete() if service_instance else None
        )

        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        mgr.bind_service(service, bk_module)

        attachments: Dict[UUID, ServiceEngineAppAttachment] = {}
        for env in bk_app.envs.all():
            for rel in mgr.list_unprovisioned_rels(env.engine_app):
                rel.provision()
                attachments[rel.db_obj.service_instance_id] = rel.db_obj

        assert len(attachments) == 2

        cleaner = ModuleCleaner(bk_module)
        cleaner.delete_services(svc.uuid)

        for instance_id in attachments:
            rel = mgr.get_unbound_instance_rel_by_instance_id(svc, instance_id)
            assert rel.db_obj.service_instance_id in attachments
            assert rel.db_obj.service_id == attachments[rel.db_obj.service_instance_id].service_id
            assert rel.db_obj.engine_app == attachments[rel.db_obj.service_instance_id].engine_app
            rel.recycle_resource()

        for instance_id in attachments:
            with pytest.raises(UnboundSvcAttachmentDoesNotExist):
                mgr.get_unbound_instance_rel_by_instance_id(svc, instance_id)
