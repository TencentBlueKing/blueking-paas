# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from unittest import mock

import pytest

from paasng.dev_resources.servicehub.remote import collector
from paasng.dev_resources.servicehub.remote.store import get_remote_store
from tests.dev_resources.servicehub.utils import gen_plan, gen_service
from tests.utils.api import mock_json_response
from tests.utils.helpers import configure_regions
from tests.utils.mocks.engine import replace_cluster_service

from . import data_mocks


@pytest.fixture()
def bk_service_r1():
    return gen_service(region="r1")


@pytest.fixture()
def bk_plan_r1_v1():
    return gen_plan(region="r1", specifications={"version": "1", "app_zone": "1"})


@pytest.fixture()
def bk_plan_r1_v2():
    return gen_plan(region="r1", specifications={"version": "2", "app_zone": "1"})


@pytest.fixture()
def bk_plan_r2_v1():
    return gen_plan(region="r2", specifications={"version": "1", "app_zone": "2"})


@pytest.fixture(autouse=True)
def _setup_regions():
    """Setup regions which were used in mocked data"""
    with configure_regions(['r1', 'r2', 'r3', 'rr1', 'rr2']), replace_cluster_service():
        yield


@pytest.fixture
def faked_remote_services():
    """Stores some faked remote services"""
    store = get_remote_store()
    config_json = {
        'name': 'obj_store_remote',
        'endpoint_url': 'http://faked-host',
        'provision_params_tmpl': {'username': '{engine_app.name}'},
        'jwt_auth_conf': {'iss': 'foo', 'key': 's1'},
    }
    meta_info = {'version': None}
    with mock.patch('requests.get') as mocked_get:
        # Mock requests response
        mocked_get.return_value = mock_json_response(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON)

        config = collector.RemoteSvcConfig.from_json(config_json)
        fetcher = collector.RemoteSvcFetcher(config)
        store.bulk_upsert(fetcher.fetch(), meta_info=meta_info, source_config=config)

    yield
    store.empty()
