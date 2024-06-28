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

from pathlib import Path
from unittest import mock

import pytest

from paasng.accessories.servicehub.remote import store as store_m
from paasng.accessories.servicehub.remote.client import RemoteSvcConfig
from paasng.accessories.servicehub.remote.store import MemoryStore, get_remote_store
from tests.paasng.platform.mgrlegacy.utils import get_migration_instance
from tests.utils.helpers import configure_regions


def pytest_collection_modifyitems(config, items):
    # pytest_collection_modifyitems always receives all collected items,
    # not only those under the conftest.py where it is implemented.
    rootdir = Path(__file__).parent
    for item in items:
        try:
            if Path(item.fspath).relative_to(rootdir):
                item.add_marker(pytest.mark.xdist_group(name="legacy-db"))
        except ValueError:
            continue


@pytest.fixture(autouse=True)
def _configure_ieod_region():
    region_list = ["ieod"]
    with configure_regions(region_list):
        yield


@pytest.fixture()
def migration_instance_maker(bk_app, legacy_app_code):
    def maker(migration_cls):
        instance = get_migration_instance(migration_cls)
        instance.context.app = bk_app
        return instance

    return maker


@pytest.fixture()
def svc_config():
    return RemoteSvcConfig.from_json(
        {
            "name": "obj_store_remote",
            "endpoint_url": "http://faked-host",
            "provision_params_tmpl": {"username": "{engine_app.name}"},
            "jwt_auth_conf": {"iss": "foo", "key": "s1"},
        }
    )


@pytest.fixture()
def store():
    """Mocked Store"""
    old_store = get_remote_store()
    memory_store = MemoryStore()
    store_m._g_services_store = memory_store
    assert get_remote_store() is memory_store
    yield memory_store
    store_m._g_services_store = old_store


@pytest.fixture(autouse=True)
def _mock_setup_log():
    with mock.patch("paasng.accessories.log.shim.EnvClusterService") as fake_log:
        fake_log().get_cluster().has_feature_flag.return_value = False
        yield
