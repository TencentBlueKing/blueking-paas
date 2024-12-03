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

import logging
from copy import deepcopy
from unittest import mock

import pytest

from paasng.accessories.servicehub.constants import Category
from paasng.accessories.servicehub.remote import collector
from paasng.accessories.servicehub.remote.exceptions import ServiceConfigNotFound, ServiceNotFound
from tests.paasng.accessories.servicehub import data_mocks
from tests.utils.api import mock_json_response

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.xdist_group(name="remote-services")]


class TestRemoteStore:
    @pytest.fixture(autouse=True)
    def _setup_data(self, config, raw_store):
        meta_info = {"version": None}
        with mock.patch("requests.get") as mocked_get:
            # Mock requests response
            mocked_get.return_value = mock_json_response(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON)
            fetcher = collector.RemoteSvcFetcher(config)
            raw_store.bulk_upsert(fetcher.fetch(), meta_info=meta_info, source_config=config)
            yield
            raw_store.empty()

    def test_get_non_exists(self, store):
        with pytest.raises(ServiceNotFound):
            store.get("invalid-uuid")

    def test_get_normal(self, store):
        uuid = data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"]
        obj = store.get(uuid)
        assert obj is not None

    def test_list_all(self, store):
        assert len(store.filter("r1")) == 2
        assert len(store.filter("r2")) == 1

    def test_list_by_category(self, store):
        assert len(store.filter("r1", conditions={"category": Category.DATA_STORAGE})) == 1

    def test_get_source_config(self, config, store):
        uuid = data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"]
        assert store.get_source_config(uuid) == config

    def test_bulk_get(self, store):
        uuids = [
            data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"],
            data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[1]["uuid"],
        ]
        services = store.bulk_get(uuids, "r1")

        assert len(services) == 2
        assert services[0]["uuid"] == uuids[0]
        assert services[1]["uuid"] == uuids[1]

    def test_bulk_get_unregistered_service(self, store):
        uuids = [data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"], "x"]
        services = store.bulk_get(uuids, "r1")

        assert len(services) == 2
        assert services[0]["uuid"] == uuids[0]
        assert services[1] is None

    def test_all(self, store):
        uuids = {i["uuid"] for i in store.all()}
        for i in data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON:
            assert i["uuid"] in uuids

    def test_empty(self, raw_store):
        store = raw_store
        assert len(store.all()) > 0

        uuid = data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON[0]["uuid"]
        store.empty()

        with pytest.raises(ServiceNotFound):
            store.get(uuid, "r1")

        with pytest.raises(ServiceConfigNotFound):
            store.get_source_config(uuid)

    def test_bulk_update_conflict(self, store, config):
        config_json = config.to_json()
        meta_info = {"version": None}
        # 增强服务的普通配置信息可以更新
        config_json["is_ready"] = False
        config_json["endpoint_url"] = "http://faked-host-new"
        store.bulk_upsert(deepcopy(store.all()), meta_info, collector.RemoteSvcConfig.from_json(config_json))

        # 增强服务的名称不能更新
        config_json["name"] = "xman"
        with pytest.raises(ValueError, match=r".* already exists"):
            store.bulk_upsert(deepcopy(store.all()), meta_info, collector.RemoteSvcConfig.from_json(config_json))
