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

import pytest
from django.urls import reverse
from django_dynamic_fixture import G
from rest_framework import status

from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.core.tenant.user import DEFAULT_TENANT_ID

pytestmark = pytest.mark.django_db


class TestUpdatePlan:
    @pytest.fixture()
    def plan(self) -> Plan:
        service = G(Service, name="mysql", category=G(ServiceCategory), logo_b64="dummy")
        return G(
            Plan,
            name="default",
            service=service,
            config=json.dumps({"host": "127.0.0.1"}),
            tenant_id=DEFAULT_TENANT_ID,
        )

    def _update(self, client, plan: Plan, data: dict):
        url = reverse(
            "plat_mgt.infras.services.plans.detail",
            kwargs={"service_id": plan.service.uuid, "tenant_id": plan.tenant_id, "plan_id": plan.uuid},
        )
        return client.put(url, data=data, format="json")

    def test_keep_config_when_absent(self, plat_mgt_api_client, plan):
        resp = self._update(
            plat_mgt_api_client, plan, {"name": "new-name", "description": "new-desc", "is_active": False}
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        plan.refresh_from_db()
        assert plan.name == "new-name"
        assert plan.is_active is False
        assert json.loads(plan.config) == {"host": "127.0.0.1"}

    def test_update_config(self, plat_mgt_api_client, plan):
        resp = self._update(
            plat_mgt_api_client,
            plan,
            {"name": "default", "description": "desc", "is_active": True, "config": {"host": "10.0.0.1"}},
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        plan.refresh_from_db()
        assert json.loads(plan.config) == {"host": "10.0.0.1"}
