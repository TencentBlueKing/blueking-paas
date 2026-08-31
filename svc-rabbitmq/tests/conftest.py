# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from unittest.mock import MagicMock, create_autospec

import pytest
from paas_service.models import Plan, Service, ServiceInstance
from vendor.client import ManagementClient, VirtualHostHandler
from vendor.clusters import Cluster

DEFAULT_INSTANCE_CREDENTIALS = {
    "host": "127.0.0.1",
    "port": 5672,
    "user": "user",
    "password": "secret",
    "vhost": "vhost",
}


@pytest.fixture()
def mock_client() -> MagicMock:
    """Fixture to provide a mocked ManagementClient."""

    client: ManagementClient = create_autospec(ManagementClient, instance=True)
    # Ensure nested handlers are plain MagicMocks for easy assertion
    client.virtual_host = MagicMock(spec=VirtualHostHandler)
    client.user_policy = MagicMock()
    client.limit_policy = MagicMock()
    client.exchange = MagicMock()
    client.queue = MagicMock()
    client.user = MagicMock()

    return client


@pytest.fixture
def service(db) -> Service:
    """真实的增强服务，供方案 / 实例 fixture 复用。"""
    return Service.objects.create(
        name="rabbitmq",
        category=1,
        display_name_zh_cn="RabbitMQ",
        display_name_en="RabbitMQ",
    )


@pytest.fixture
def plan(service) -> Plan:
    """未开启 stream 的默认方案。"""
    return Plan.objects.create(
        name="plan-default",
        properties={},
        service=service,
        config=json.dumps({}),
    )


@pytest.fixture
def instance(service, plan) -> ServiceInstance:
    """绑定到默认方案的存量实例，凭证里还没有 stream_port。"""
    return ServiceInstance.objects.create(
        service=service,
        plan=plan,
        credentials=json.dumps(DEFAULT_INSTANCE_CREDENTIALS),
        tenant_id=plan.tenant_id,
    )


def make_cluster(version: str = "3.9.0", **overrides) -> Cluster:
    """Build a Cluster pydantic model for testing."""

    defaults = {
        "host": "127.0.0.1",
        "port": 5672,
        "management_api": "http://127.0.0.1:15672",
        "admin": "admin",
        "password": "password",
        "version": version,
        "tls": {},
    }
    defaults.update(overrides)

    return Cluster(**defaults)
