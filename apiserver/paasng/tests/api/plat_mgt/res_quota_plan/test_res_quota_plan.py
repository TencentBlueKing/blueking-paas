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

from paas_wl.bk_app.cnative.specs.models import ResQuotaPlan

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestResourceQuotaPlanViewSet:
    """测试平台管理 - 资源配额方案管理 API"""

    @pytest.fixture()
    def sample_plan_data(self):
        return {
            "plan_name": "test-plan",
            "cpu_limit": "4000m",
            "memory_limit": "2048Mi",
            "cpu_request": "1000m",
            "memory_request": "512Mi",
            "is_active": True,
        }

    @pytest.fixture()
    def created_plan(self, sample_plan_data):
        """创建测试用的资源配额方案"""
        return ResQuotaPlan.objects.create(**sample_plan_data)

    def test_list_empty(self, plat_mgt_api_client):
        url = reverse("plat_mgt.res_quota_plans.list_create")
        response = plat_mgt_api_client.get(url)
        assert response.status_code == 200
        assert response.data == []

    def test_list_with_plans(self, plat_mgt_api_client, created_plan, sample_plan_data):
        url = reverse("plat_mgt.res_quota_plans.list_create")
        response = plat_mgt_api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1
        plan = response.data[0]
        assert plan["plan_name"] == sample_plan_data["plan_name"]
        assert plan["cpu_limit"] == sample_plan_data["cpu_limit"]
        assert plan["memory_limit"] == sample_plan_data["memory_limit"]

    def test_create_success(self, plat_mgt_api_client, sample_plan_data):
        url = reverse("plat_mgt.res_quota_plans.list_create")
        response = plat_mgt_api_client.post(url, data=sample_plan_data)
        assert response.status_code == 201
        assert ResQuotaPlan.objects.filter(plan_name=sample_plan_data["plan_name"]).exists()

    def test_create_duplicate_name(self, plat_mgt_api_client, sample_plan_data, created_plan):
        url = reverse("plat_mgt.res_quota_plans.list_create")
        response = plat_mgt_api_client.post(url, data=sample_plan_data)
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "field",
        ["cpu_limit", "cpu_request", "memory_limit", "memory_request"],
    )
    def test_create_invalid_resource_value(self, plat_mgt_api_client, sample_plan_data, field):
        url = reverse("plat_mgt.res_quota_plans.list_create")
        sample_plan_data[field] = "invalid"
        response = plat_mgt_api_client.post(url, data=sample_plan_data)
        assert response.status_code == 400

    def test_update_success(self, plat_mgt_api_client, created_plan, sample_plan_data):
        url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": created_plan.id})
        update_data = sample_plan_data.copy()
        update_data["plan_name"] = "updated-plan"
        update_data["cpu_limit"] = "8000m"

        response = plat_mgt_api_client.put(url, data=update_data)
        assert response.status_code == 200

        created_plan.refresh_from_db()
        assert created_plan.plan_name == "updated-plan"
        assert created_plan.cpu_limit == "8000m"

    def test_update_with_same_name(self, plat_mgt_api_client, created_plan, sample_plan_data):
        url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": created_plan.id})
        update_data = sample_plan_data.copy()
        update_data["cpu_limit"] = "8000m"

        response = plat_mgt_api_client.put(url, data=update_data)
        assert response.status_code == 200

        created_plan.refresh_from_db()
        assert created_plan.plan_name == sample_plan_data["plan_name"]
        assert created_plan.cpu_limit == "8000m"

    def test_update_duplicate_name(self, plat_mgt_api_client, created_plan, sample_plan_data):
        another_plan_data = sample_plan_data.copy()
        another_plan_data["plan_name"] = "another-plan"
        plan2 = ResQuotaPlan.objects.create(**another_plan_data)

        update_url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": plan2.id})
        update_data = another_plan_data.copy()
        update_data["plan_name"] = created_plan.plan_name

        response = plat_mgt_api_client.put(update_url, data=update_data)
        assert response.status_code == 400

    def test_destroy_success(self, plat_mgt_api_client, created_plan):
        url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": created_plan.id})
        response = plat_mgt_api_client.delete(url)
        assert response.status_code == 204
        assert not ResQuotaPlan.objects.filter(id=created_plan.id).exists()

    def test_destroy_not_found(self, plat_mgt_api_client):
        url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": 99999})
        response = plat_mgt_api_client.delete(url)
        assert response.status_code == 404

    def test_get_quantity_options(self, plat_mgt_api_client):
        url = reverse("plat_mgt.res_quota_plans.quantity_options")
        response = plat_mgt_api_client.get(url)
        assert response.status_code == 200
        assert "cpu_resource_quantity" in response.data
        assert "memory_resource_quantity" in response.data

        cpu_options = response.data["cpu_resource_quantity"]
        assert len(cpu_options) > 0
        assert all("value" in opt and "label" in opt for opt in cpu_options)

        memory_options = response.data["memory_resource_quantity"]
        assert len(memory_options) > 0
        assert all("value" in opt and "label" in opt for opt in memory_options)
