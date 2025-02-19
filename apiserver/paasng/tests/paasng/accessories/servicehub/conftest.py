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

from unittest import mock

import pytest
from django.conf import settings
from django_dynamic_fixture import G

from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.remote import collector
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from tests.paasng.accessories.servicehub import data_mocks
from tests.utils.api import mock_json_response
from tests.utils.helpers import generate_random_string


@pytest.fixture()
def _faked_remote_services():
    """Stores some faked remote services"""
    store = get_remote_store()
    config_json = {
        "name": "obj_store_remote",
        "endpoint_url": "http://faked-host",
        "provision_params_tmpl": {"username": "{engine_app.name}", "tenant_id": "{application.tenant_id}"},
        "jwt_auth_conf": {"iss": "foo", "key": "s1"},
    }
    meta_info = {"version": None}
    with mock.patch("requests.get") as mocked_get:
        # Mock requests response
        mocked_get.return_value = mock_json_response(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON)

        config = collector.RemoteSvcConfig.from_json(config_json)
        fetcher = collector.RemoteSvcFetcher(config)
        store.bulk_upsert(fetcher.fetch(), meta_info=meta_info, source_config=config)

    yield
    store.empty()


@pytest.fixture()
def local_service():
    service = G(
        Service, name="mysql", category=G(ServiceCategory), region=settings.DEFAULT_REGION_NAME, logo_b64="dummy"
    )
    # Create some plans
    G(Plan, name=generate_random_string(), service=service)
    G(Plan, name=generate_random_string(), service=service)
    return mixed_service_mgr.get(service.uuid)


@pytest.fixture()
@pytest.mark.usefixture("_faked_remote_services")
def remote_service(_faked_remote_services):
    return mixed_service_mgr.get(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"])


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
    return service_obj.get_plans()[0]


@pytest.fixture
def plan2(service_obj):
    return service_obj.get_plans()[1]
