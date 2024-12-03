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
from json import dumps
from typing import Dict
from unittest import mock
from uuid import UUID

import pytest
from django_dynamic_fixture import G

from paasng.accessories.servicehub.constants import Category
from paasng.accessories.servicehub.exceptions import BindServiceNoPlansError, ServiceObjNotFound
from paasng.accessories.servicehub.local import LocalServiceMgr, LocalServiceObj
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import ServiceEngineAppAttachment
from paasng.accessories.servicehub.remote import RemoteServiceObj
from paasng.accessories.servicehub.services import ServiceInstanceObj
from paasng.accessories.services.models import Plan, Service, ServiceCategory, ServiceInstance
from tests.paasng.accessories.servicehub import data_mocks

pytestmark = [pytest.mark.django_db, pytest.mark.xdist_group(name="remote-services")]


@pytest.mark.usefixtures("_faked_remote_services")
class TestMixedMgr:
    def test_list_by_category(self):
        services = list(mixed_service_mgr.list_by_category("r1", category_id=Category.DATA_STORAGE))
        assert len(services) == 1

        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        G(Service, category=category, region="r1", logo_b64="dummy")
        G(Service, category=category, region="r2", logo_b64="dummy")

        services = list(mixed_service_mgr.list_by_category("r1", category_id=Category.DATA_STORAGE))
        assert len(services) == 2

    def test_list_by_region(self):
        services = list(mixed_service_mgr.list_by_region("r1"))
        assert len(services) == 2

        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        G(Service, category=category, region="r1", logo_b64="dummy")
        G(Service, category=category, region="r2", logo_b64="dummy")

        services = list(mixed_service_mgr.list_by_region("r1"))
        assert len(services) == 3

    def test_get_remote_found(self):
        obj = mixed_service_mgr.get(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"])
        assert obj is not None

    def test_get_local_found(self):
        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        svc = G(Service, category=category, region="r1", logo_b64="dummy")

        obj = mixed_service_mgr.get(str(svc.uuid))
        assert obj is not None

    def test_get_not_found(self):
        with pytest.raises(ServiceObjNotFound):
            mixed_service_mgr.get(uuid="f" * 64)

    def test_find_by_name_local_found(self):
        # Add a service in database
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        svc = G(Service, category=category, region="r1", logo_b64="dummy")

        obj = mixed_service_mgr.find_by_name(str(svc.name), region="r1")
        assert obj is not None
        assert isinstance(obj, LocalServiceObj)
        assert not isinstance(obj, RemoteServiceObj)

    def test_find_by_name_remote_found(self):
        obj = mixed_service_mgr.find_by_name(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["name"], region="r1")
        assert obj is not None
        assert not isinstance(obj, LocalServiceObj)
        assert isinstance(obj, RemoteServiceObj)

    def test_find_by_name_not_found(self):
        with pytest.raises(ServiceObjNotFound):
            mixed_service_mgr.find_by_name("non-exists-name", region="r1")

    @mock.patch("paasng.accessories.servicehub.manager.MixedServiceMgr.list_provisioned_rels")
    def test_get_env_vars_ordering(self, mock_list_provisioned_rels):
        def create_mock_rel(create_time: "datetime.datetime", **credentials):
            rel = mock.MagicMock()
            rel.get_instance.return_value = ServiceInstanceObj(
                uuid="", credentials=credentials, config={}, create_time=create_time
            )
            return rel

        mock_list_provisioned_rels.return_value = [
            create_mock_rel(datetime.datetime(2020, 1, 3), c=3),
            create_mock_rel(datetime.datetime(2020, 1, 1), a=1, b=1),
            create_mock_rel(datetime.datetime(2020, 1, 2), b=2, c=2),
        ]

        envs = mixed_service_mgr.get_env_vars(mock.MagicMock())
        assert envs == {"a": 1, "b": 2, "c": 3}


class TestLocalMgr:
    @pytest.fixture(autouse=True)
    def svc(self, bk_app):
        """Create a local service object."""
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        svc = G(Service, name="mysql", category=category, region=bk_app.region, logo_b64="dummy")
        # Create 2 plans
        G(Plan, name="no-ha", service=svc, config="{}")
        G(Plan, name="ha", service=svc, config="{}")
        return svc

    @pytest.fixture()
    def plan_default(self, svc):
        return Plan.objects.get(service=svc, name="no-ha")

    @pytest.fixture()
    def plan_ha(self, svc):
        return Plan.objects.get(service=svc, name="ha")

    @pytest.fixture()
    def instance_factory(self, svc, plan_default):
        """A factory method that creates an instance object."""

        def _create():
            return G(
                ServiceInstance,
                service=svc,
                plan=plan_default,
                config="{}",
                credentials=dumps({"MYSQL_USERNAME": "foo", "MYSQL_PASSWORD": "bar"}),
            )

        return _create

    def test_bind_service(self, svc, bk_module):
        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        rel_pk = mgr.bind_service(service, bk_module)
        assert rel_pk is not None

    def test_list_binded(self, svc, bk_app, bk_module):
        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        assert list(mgr.list_binded(bk_module)) == []
        for env in bk_app.envs.all():
            assert list(mgr.list_unprovisioned_rels(env.engine_app)) == []

        rel_pk = mgr.bind_service(service, bk_module)
        assert rel_pk is not None
        assert list(mgr.list_binded(bk_module)) == [service]
        for env in bk_app.envs.all():
            assert len(list(mgr.list_unprovisioned_rels(env.engine_app))) == 1

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

    def test_find_by_name_not_found(self, bk_module):
        mgr = LocalServiceMgr()
        with pytest.raises(ServiceObjNotFound):
            mgr.find_by_name(name="foo_name", region=bk_module.region)

    def test_find_by_name_normal(self, bk_module):
        mgr = LocalServiceMgr()
        service = mgr.find_by_name(name="mysql", region=bk_module.region)
        assert service is not None

    def test_module_is_bound_with(self, svc, bk_module):
        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)
        assert mgr.module_is_bound_with(service, bk_module) is False

        mgr.bind_service(service, bk_module)
        assert mgr.module_is_bound_with(service, bk_module) is True

    def test_get_attachment_by_instance_id(self, bk_module):
        expect_obj: Dict[UUID, ServiceEngineAppAttachment] = {}

        mgr = LocalServiceMgr()
        svc = mgr.find_by_name(name="mysql", region=bk_module.region)

        # 绑定服务并创建服务实例
        mgr.bind_service(svc, bk_module)
        for env in bk_module.envs.all():
            for rel in mixed_service_mgr.list_unprovisioned_rels(env.engine_app, svc):
                plan = rel.get_plan()
                if plan.is_eager:
                    rel.provision()
                    expect_obj[rel.db_obj.service_instance_id] = rel.db_obj

        for service_instance_id in expect_obj:
            assert mgr.get_attachment_by_instance_id(svc, service_instance_id) == expect_obj[service_instance_id]


class TestLocalRabbitMQMgr:
    @pytest.fixture(autouse=True)
    def svc(self, bk_app):
        """Create a local service object."""
        category = G(ServiceCategory, id=Category.DATA_STORAGE)
        svc = G(Service, name="rabbitmq", category=category, region=bk_app.region, logo_b64="dummy")
        # Create 2 inactive plans
        G(Plan, name="no-ha", service=svc, config="{}", is_active=False)
        G(Plan, name="ha", service=svc, config="{}", is_active=False)
        return svc

    def test_bind_service(self, svc, bk_module):
        mgr = LocalServiceMgr()
        service = mgr.get(svc.uuid)

        with pytest.raises(BindServiceNoPlansError):
            mgr.bind_service(service, bk_module)

    def test_list_by_category(self, svc, bk_app):
        mgr = LocalServiceMgr()
        found = False
        for service in mgr.list_by_category(
            category_id=Category.DATA_STORAGE, region=bk_app.region, include_hidden=True
        ):
            if service.uuid == str(svc.uuid):
                found = True
                break

        assert found
