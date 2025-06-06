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

from paasng.accessories.servicehub.remote.client import RemoteSvcConfig
from paasng.accessories.servicehub.remote.store import RemoteServiceStore

from .utils import gen_plan, gen_service


@pytest.fixture()
def store(raw_store, config):
    """Mocked Store"""
    with mock.patch.object(raw_store, "get_source_config") as get_source_config:
        get_source_config.return_value = config
        yield raw_store


@pytest.fixture()
def raw_store():
    return RemoteServiceStore()


@pytest.fixture()
def config():
    return RemoteSvcConfig.from_json(
        {
            "name": "obj_store_remote",
            "endpoint_url": "http://faked-host",
            "provision_params_tmpl": {"username": "{engine_app.name}"},
            "jwt_auth_conf": {"iss": "foo", "key": "s1"},
        }
    )


@pytest.fixture()
def bk_service():
    return gen_service()


@pytest.fixture()
def bk_plan_1():
    return gen_plan()


@pytest.fixture()
def bk_plan_2():
    return gen_plan()
