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

"""集群侧用内存替身代替 k8s，集群与分配策略用真实数据，以覆盖「自定义模板只下发到应用租户可分配的集群」"""

import pytest
from django_dynamic_fixture import G

from paas_wl.infras.cluster.models import Cluster, ClusterE2BConfig
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.agent_sandbox.e2b.template_sync import sync
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .fakes import NAMESPACE, OTHER_CLUSTER, FakeClusters, FakeLock


@pytest.fixture()
def clusters(monkeypatch) -> FakeClusters:
    fake = FakeClusters()
    monkeypatch.setattr(sync, "get_client_by_cluster_name", fake.client_for)
    monkeypatch.setattr(sync, "_kres", fake.kres)
    return fake


@pytest.fixture(autouse=True)
def sync_lock(monkeypatch) -> FakeLock:
    lock = FakeLock()
    monkeypatch.setattr(sync, "redis_lock", lock)
    return lock


@pytest.fixture()
def race_after_first_apply(monkeypatch):
    """在第一次下发完成后插入一段操作，模拟锁过期后另一次下发与当前下发交错执行"""

    def _install(action):
        original = sync._apply
        pending = [action]

        def _apply(client, template, namespace):
            original(client, template, namespace)
            if pending:
                pending.pop()()

        monkeypatch.setattr(sync, "_apply", _apply)

    return _install


@pytest.fixture(autouse=True)
def e2b_clusters():
    for name in (CLUSTER_NAME_FOR_TESTING, OTHER_CLUSTER):
        cluster = Cluster.objects.filter(name=name).first() or G(Cluster, name=name, tenant_id=DEFAULT_TENANT_ID)
        ClusterE2BConfig.objects.create(
            cluster=cluster,
            control_plane_url="http://e2b-gateway:8080",
            data_plane_address="e2b.example.com",
            api_key="key",
            tenant_id=DEFAULT_TENANT_ID,
            namespace=NAMESPACE,
        )
