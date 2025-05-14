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

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from paasng.core.tenant.user import OP_TYPE_TENANT_ID

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestListTenantAvailableClusters:
    """获取租户可用集群列表"""

    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with override_settings(ENABLE_MULTI_TENANT_MODE=True):
            yield

    def test_list(self, init_default_cluster, init_system_cluster, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(
            reverse("plat_mgt.infras.tenant.available_clusters", kwargs={"tenant_id": OP_TYPE_TENANT_ID})
        )
        assert resp.status_code == status.HTTP_200_OK

        assert resp.json() == [{"name": init_system_cluster.name}]
