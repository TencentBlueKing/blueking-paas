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
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from paasng.accessories.servicehub.remote.collector import initialize_remote_services
from tests.paasng.accessories.servicehub import data_mocks
from tests.utils.api import mock_json_response

pytestmark = [pytest.mark.xdist_group(name="remote-services")]


class TestInitialize:
    @override_settings(SERVICE_REMOTE_ENDPOINTS=None)
    def test_improperly_configured(self, store):
        with pytest.raises(ImproperlyConfigured):
            initialize_remote_services(store)

    @mock.patch("requests.get")
    def test_normal(self, mocked_get, config):
        mocked_get.return_value = mock_json_response(data_mocks.OBJ_STORE_REMOTE_SERVICES_JSON)
        mocked_store = mock.MagicMock()
        service_remote_endpoints = [config.to_json()]

        with override_settings(SERVICE_REMOTE_ENDPOINTS=service_remote_endpoints):
            initialize_remote_services(mocked_store)

        assert mocked_store.bulk_upsert.call_count == len(service_remote_endpoints)
        assert mocked_get.called
        assert mocked_get.call_args[0][0] == "http://faked-host/services/"
