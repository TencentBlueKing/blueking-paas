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


import uuid

import pytest
from django.urls import reverse

from paasng.platform.bkapp_model.constants import MAX_PROC_CPU, MAX_PROC_MEM
from paasng.platform.bkapp_model.models import ResQuotaPlan

pytestmark = pytest.mark.django_db(databases=["default"])


class TestResourceQuotaPlanViewSet:
    """测试平台管理 - 资源配额方案管理 API"""

    @pytest.fixture()
    def sample_plan_data(self):
        return {
            "name": "testplan",
            "limits": {"cpu": "4000m", "memory": "2048Mi"},
            "requests": {"cpu": "1000m", "memory": "512Mi"},
        }

    @pytest.fixture()
    def created_plan(self, sample_plan_data):
        """创建测试用的资源配额方案"""
        return ResQuotaPlan.objects.create(**sample_plan_data)

    def test_list_with_plans(self, plat_mgt_api_client, created_plan, sample_plan_data):
        url = reverse("plat_mgt.res_quota_plans.list_create")
        response = plat_mgt_api_client.get(url)

        assert response.status_code == 200
        assert len(response.data) >= 1
        names = [plan["name"] for plan in response.data]
        assert created_plan.name in names

    def test_create_success(self, plat_mgt_api_client, sample_plan_data):
        url = reverse("plat_mgt.res_quota_plans.list_create")
        response = plat_mgt_api_client.post(url, data=sample_plan_data)
        assert response.status_code == 201

        assert ResQuotaPlan.objects.filter(name=sample_plan_data["name"]).exists()

    def test_create_duplicate_name(self, plat_mgt_api_client, sample_plan_data, created_plan):
        url = reverse("plat_mgt.res_quota_plans.list_create")
        response = plat_mgt_api_client.post(url, data=sample_plan_data)
        assert response.status_code == 400

    def test_update_success(self, plat_mgt_api_client, created_plan, sample_plan_data):
        url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": created_plan.id})
        update_data = sample_plan_data.copy()
        update_data["name"] = "updatedplan"
        update_data["limits"] = {"cpu": "8000m", "memory": "4096Mi"}
        update_data["requests"] = {"cpu": "2000m", "memory": "1Gi"}

        response = plat_mgt_api_client.put(url, data=update_data)
        assert response.status_code == 200

        created_plan.refresh_from_db()
        assert created_plan.name == "updatedplan"
        assert created_plan.limits == {"cpu": "8000m", "memory": "4096Mi"}
        assert created_plan.requests == {"cpu": "2000m", "memory": "1Gi"}

    def test_update_with_same_name(self, plat_mgt_api_client, created_plan, sample_plan_data):
        url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": created_plan.id})
        update_data = sample_plan_data.copy()
        update_data["limits"] = {"cpu": "8000m", "memory": "4096Mi"}

        response = plat_mgt_api_client.put(url, data=update_data)
        assert response.status_code == 200

        created_plan.refresh_from_db()
        assert created_plan.limits == {"cpu": "8000m", "memory": "4096Mi"}
        assert created_plan.requests == {"cpu": "1000m", "memory": "512Mi"}

    def test_update_duplicate_name(self, plat_mgt_api_client, created_plan, sample_plan_data):
        another_plan_data = sample_plan_data.copy()
        another_plan_data["name"] = "another-plan"
        plan2 = ResQuotaPlan.objects.create(**another_plan_data)

        update_url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": plan2.id})
        update_data = another_plan_data.copy()
        update_data["name"] = created_plan.name

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

    def test_update_builtin_plan_forbidden(self, plat_mgt_api_client, sample_plan_data):
        """测试内置方案不允许修改"""
        builtin_plan = ResQuotaPlan.objects.create(
            name="builtin-plan",
            limits={"cpu": "4000m", "memory": "2048Mi"},
            requests={"cpu": "1000m", "memory": "512Mi"},
            is_builtin=True,
        )

        url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": builtin_plan.id})
        update_data = sample_plan_data.copy()
        update_data["name"] = "updated-builtin"

        response = plat_mgt_api_client.put(url, data=update_data)
        assert response.status_code == 403

    def test_destroy_builtin_plan_forbidden(self, plat_mgt_api_client):
        """测试内置方案不允许删除"""
        builtin_plan = ResQuotaPlan.objects.create(
            name="builtin-plan-delete",
            limits={"cpu": "4000m", "memory": "2048Mi"},
            requests={"cpu": "1000m", "memory": "512Mi"},
            is_builtin=True,
        )

        url = reverse("plat_mgt.res_quota_plans.update_destroy", kwargs={"pk": builtin_plan.id})
        response = plat_mgt_api_client.delete(url)
        assert response.status_code == 403
        # 确认方案仍然存在
        assert ResQuotaPlan.objects.filter(id=builtin_plan.id).exists()

    @pytest.mark.parametrize(
        ("limits", "requests", "expected_status"),
        [
            ({"cpu": "1000", "memory": "2048Mi"}, {"cpu": "1000m", "memory": "512Mi"}, 400),
            ({"cpu": "-1000m", "memory": "2048Mi"}, {"cpu": "1000m", "memory": "512Mi"}, 400),
            ({"cpu": "xyz0m", "memory": "2048Mi"}, {"cpu": "1000m", "memory": "512Mi"}, 400),
            ({"cpu": "1000m", "memory": "2048"}, {"cpu": "1000m", "memory": "512Mi"}, 400),
            ({"cpu": "1000m", "memory": "-2048Mi"}, {"cpu": "1000m", "memory": "512Mi"}, 400),
            ({"cpu": "1000m", "memory": "xyz0Mi"}, {"cpu": "1000m", "memory": "512Mi"}, 400),
            # requests 超过 limits
            ({"cpu": "4000m", "memory": "2048Mi"}, {"cpu": "5000m", "memory": "512Mi"}, 400),
            ({"cpu": "4000m", "memory": "2048Mi"}, {"cpu": "1000m", "memory": "3Gi"}, 400),
            # 最大允许值
            ({"cpu": MAX_PROC_CPU, "memory": MAX_PROC_MEM}, {"cpu": MAX_PROC_CPU, "memory": MAX_PROC_MEM}, 201),
            # 超过最大值
            ({"cpu": f"{int(MAX_PROC_CPU[:-1]) + 1}m", "memory": "2048Mi"}, {"cpu": "1000m", "memory": "512Mi"}, 400),
        ],
    )
    def test_resource_validation(self, plat_mgt_api_client, limits, requests, expected_status):
        """统一测试资源配额方案的各种验证场景"""
        url = reverse("plat_mgt.res_quota_plans.list_create")
        data = {
            "name": f"validationTestPlan{uuid.uuid4().hex[:8]}",
            "limits": limits,
            "requests": requests,
        }

        response = plat_mgt_api_client.post(url, data=data)
        assert response.status_code == expected_status

    def test_list_quantity_options(self, plat_mgt_api_client):
        url = reverse("plat_mgt.res_quota_plans.list_quantity_options")
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
