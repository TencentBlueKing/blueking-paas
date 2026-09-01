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

import pytest

from paas_wl.infras.cluster.models import Cluster, ClusterE2BConfig
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

# 改写后应当出现在响应里的对外地址，与网关自报的集群内地址刻意取得毫不相似，
# 断言时不会因为子串巧合而误判
DATA_PLANE_ADDRESS = "e2b.example.com"
GATEWAY_INTERNAL_DOMAIN = "e2b-sandbox-gateway.bcs-system.svc.cluster.local"


@pytest.fixture()
def e2b_config() -> ClusterE2BConfig:
    """给测试集群登记一份 e2b 配置。"""
    return ClusterE2BConfig.objects.create(
        cluster=Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING),
        control_plane_url="http://e2b-gateway.bcs-system:8080",
        data_plane_address=DATA_PLANE_ADDRESS,
        api_key="e2b_real_gateway_key",
        tenant_id=DEFAULT_TENANT_ID,
    )
