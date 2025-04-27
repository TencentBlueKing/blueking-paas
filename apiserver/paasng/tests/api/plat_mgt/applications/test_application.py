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
from django.urls import reverse

pytestmark = pytest.mark.django_db


from paasng.platform.applications.models import Application


class TestApplicationListView:
    """测试平台管理 - 应用列表 API"""

    def test_list_applications(self, plat_mgt_api_client, tenant_mgt_api_client):
        """测试获取应用列表"""

        # 准备数据
        Application.objects.create(code="app1", name="应用1", tenant_id="plat_tenant")
        Application.objects.create(code="app2", name="应用2", tenant_id="tenant1")
        Application.objects.create(code="app3", name="应用3", tenant_id="tenant2")

        url = reverse("plat_mgt.applications.list_applications")
        # 平台管理员获取所有应用
        response = plat_mgt_api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 3

    def test_retrieve_application(self, plat_mgt_api_client, tenant_mgt_api_client):
        """测试获取单个应用的详细信息"""

        # 准备数据
        app = Application.objects.create(code="app1", name="应用1", tenant_id="plat_tenant")
        url = reverse("plat_mgt.applications.retrieve_application", args=[app.code])

        # 平台管理员获取应用信息
        response = plat_mgt_api_client.get(url)
        assert response.status_code == 200
        assert response.data["code"] == app.code
