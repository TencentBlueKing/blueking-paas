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
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.constants import Category
from paasng.accessories.servicehub.exceptions import DuplicatedServiceBoundError, ReferencedAttachmentNotFound
from paasng.accessories.servicehub.manager import SharedServiceInfo, mixed_service_mgr
from paasng.accessories.servicehub.models import ServiceInstance
from paasng.accessories.servicehub.services import ServiceObj
from paasng.accessories.servicehub.sharing import ServiceSharingManager, SharingReferencesManager
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.modules.models import Module
from tests.utils.basic import generate_random_string
from tests.utils.helpers import create_app, initialize_module

from . import data_mocks

pytestmark = [
    pytest.mark.django_db(databases=["default", "workloads"]),
    pytest.mark.xdist_group(name="remote-services"),
]


def create_module(bk_app):
    module = Module.objects.create(
        region=bk_app.region, application=bk_app, name=generate_random_string(length=8), creator=bk_app.creator
    )
    initialize_module(module)
    return module


@pytest.fixture()
def local_service(request):
    service = G(Service, name="mysql", category=G(ServiceCategory), logo_b64="dummy")
    G(Plan, name="plan-1", service=service)
    G(Plan, name="plan-2", service=service)
    return mixed_service_mgr.get(service.uuid)


@pytest.fixture()
def remote_service(_faked_remote_services):
    return mixed_service_mgr.get(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"])


def pick_different_category(service_obj: ServiceObj) -> int:
    """Pick a category different with given service object"""
    for category in Category:
        if category != service_obj.category_id:
            return category
    raise RuntimeError("Can not found a wrong category")


@pytest.fixture(params=["local", "remote"])
def service_obj(request, local_service, remote_service):
    """
    Service object for testing, this fixture will yield both a remote and a local service
    """
    if request.param == "remote":
        return request.getfixturevalue("remote_service")
    elif request.param == "local":
        return request.getfixturevalue("local_service")
    else:
        raise ValueError("Invalid type_ parameter")


@pytest.fixture()
def ref_module(bk_app, bk_module, service_obj):
    """A fixture which creates a module that referenced by sharing manager."""
    return create_module(bk_app)


class TestServiceSharingManager:
    @pytest.fixture(autouse=True)
    def _with_static_binding_policy(self, service_obj):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[service_obj.get_plans()[0].uuid])

    def test_list_shareable(self, bk_app, bk_module, service_obj):
        # Bind source module with a remote service
        ref_module = create_module(bk_app)
        mixed_service_mgr.bind_service(service_obj, ref_module)

        assert ServiceSharingManager(bk_module).list_shareable(service_obj) == [ref_module]
        assert ServiceSharingManager(ref_module).list_shareable(service_obj) == []

    def test_create(self, bk_app, bk_module, service_obj):
        # Bind source module with a remote service
        ref_module = create_module(bk_app)
        mixed_service_mgr.bind_service(service_obj, ref_module)

        assert ServiceSharingManager(bk_module).create(service_obj, ref_module) is not None

    def test_create_already_bound(self, bk_app, bk_module, service_obj):
        ref_module = create_module(bk_app)
        mixed_service_mgr.bind_service(service_obj, ref_module)
        # bind service beforehand
        mixed_service_mgr.bind_service(service_obj, bk_module)

        with pytest.raises(DuplicatedServiceBoundError):
            ServiceSharingManager(bk_module).create(service_obj, ref_module)

    def test_bind_already_shared(self, bk_app, bk_module, service_obj):
        ref_module = create_module(bk_app)
        mixed_service_mgr.bind_service(service_obj, ref_module)
        # Create sharing relationship beforehand
        ServiceSharingManager(bk_module).create(service_obj, ref_module)

        with pytest.raises(DuplicatedServiceBoundError):
            mixed_service_mgr.bind_service(service_obj, bk_module)

    def test_create_with_other_app(self, bk_user, bk_app, bk_module, service_obj):
        another_app = create_app(owner_username=bk_user.username)
        ref_module = another_app.get_default_module()
        mixed_service_mgr.bind_service(service_obj, ref_module)

        with pytest.raises(ReferencedAttachmentNotFound):
            ServiceSharingManager(bk_module).create(service_obj, ref_module)

    def test_get_shared_info(self, bk_user, bk_app, bk_module, service_obj, ref_module):
        sharing_mgr = ServiceSharingManager(bk_module)
        mixed_service_mgr.bind_service(service_obj, ref_module)
        ServiceSharingManager(bk_module).create(service_obj, ref_module)

        info = sharing_mgr.get_shared_info(service_obj)
        assert isinstance(info, SharedServiceInfo)

    def test_list_shared_info(self, bk_user, bk_app, bk_module, service_obj, ref_module):
        sharing_mgr = ServiceSharingManager(bk_module)
        mixed_service_mgr.bind_service(service_obj, ref_module)
        ServiceSharingManager(bk_module).create(service_obj, ref_module)

        infos = sharing_mgr.list_shared_info(service_obj.category_id)
        assert len(infos) == 1
        assert infos[0].module == bk_module
        assert infos[0].ref_module == ref_module
        assert infos[0].service == service_obj

        # List another category
        infos = sharing_mgr.list_shared_info(pick_different_category(service_obj))
        assert infos == []


class TestSharingReferencesManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self, bk_module, ref_module, service_obj):
        SvcBindingPolicyManager(service_obj, DEFAULT_TENANT_ID).set_uniform(plans=[service_obj.get_plans()[0].uuid])

        # Create sharing relationship
        mixed_service_mgr.bind_service(service_obj, ref_module)
        ServiceSharingManager(bk_module).create(service_obj, ref_module)

    def test_list_related_modules(self, bk_user, bk_app, bk_module, service_obj, ref_module):
        modules = SharingReferencesManager(ref_module).list_related_modules(service_obj)
        assert modules == [bk_module]

    def test_clear_related(self, bk_module, service_obj, ref_module):
        sharing_mgr = ServiceSharingManager(bk_module)

        assert len(sharing_mgr.list_shared_info(service_obj.category_id)) == 1
        SharingReferencesManager(ref_module).clear_related(service_obj)
        # Shared info should be empty after clearing related relationships
        assert len(sharing_mgr.list_shared_info(service_obj.category_id)) == 0


class TestGetEnvVariables:
    @pytest.fixture(autouse=True)
    def _with_static_binding_policy(self, local_service):
        """Initialize the service binding policy for local service."""
        service = mixed_service_mgr.get(local_service.uuid)
        SvcBindingPolicyManager(local_service, DEFAULT_TENANT_ID).set_uniform(plans=[service.get_plans()[0].uuid])

    def test_local_integrated(self, bk_app, bk_module, local_service):
        def _create_instance():
            """mocked function which creates a faked service instance"""
            svc = Service.objects.get(pk=local_service.uuid)
            return G(
                ServiceInstance,
                service=svc,
                plan=Plan.objects.filter(service=svc)[0],
                config="{}",
                credentials=json.dumps({"FOO": "1"}),
            )

        # Bind source module with a remote service
        ref_module = create_module(bk_app)
        mixed_service_mgr.bind_service(local_service, ref_module)

        # Create real service instance data for ref_module
        with mock.patch("paasng.accessories.services.models.Service.create_service_instance_by_plan") as mocker:
            mocker.side_effect = [_create_instance(), _create_instance()]
            for env in ref_module.envs.all():
                for rel in mixed_service_mgr.list_unprovisioned_rels(env.engine_app):
                    rel.provision()

        # Get shared env variables
        env = bk_module.get_envs("prod")
        ret = ServiceSharingManager(bk_module).get_env_variables(env)
        assert ret == {}

        ServiceSharingManager(bk_module).create(local_service, ref_module)
        ret = ServiceSharingManager(bk_module).get_env_variables(env)
        assert ret == {"FOO": "1"}

        ServiceSharingManager(bk_module).destroy(local_service)
        ret = ServiceSharingManager(bk_module).get_env_variables(env)
        assert ret == {}
