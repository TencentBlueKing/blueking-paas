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

from paasng.platform.bkapp_model.models import ResQuotaPlan

pytestmark = pytest.mark.django_db


class TestResQuotaPlanOptionsView:
    @pytest.fixture()
    def plans(self, bk_app):
        public = ResQuotaPlan.objects.create(
            name="public-dev-plan",
            limits={"cpu": "1000m", "memory": "1024Mi"},
            requests={"cpu": "200m", "memory": "256Mi"},
            is_active=True,
        )
        dedicated = ResQuotaPlan.objects.create(
            name="dedicated-dev-plan",
            limits={"cpu": "2000m", "memory": "4096Mi"},
            requests={"cpu": "2000m", "memory": "4096Mi"},
            is_active=True,
            allowed_app_codes=[bk_app.code],
        )
        other = ResQuotaPlan.objects.create(
            name="other-dev-plan",
            limits={"cpu": "2000m", "memory": "4096Mi"},
            requests={"cpu": "2000m", "memory": "4096Mi"},
            is_active=True,
            allowed_app_codes=["someone-else"],
        )
        return public, dedicated, other

    def test_without_app_code_only_public(self, api_client, plans):
        public, dedicated, other = plans
        response = api_client.get("/api/bkapps/quota_plans/")
        assert response.status_code == 200
        names = {item["name"] for item in response.data}
        assert public.name in names
        assert dedicated.name not in names
        assert other.name not in names
        assert all("allowed_app_codes" not in item for item in response.data)

    def test_with_app_code_includes_dedicated(self, api_client, bk_app, plans):
        public, dedicated, other = plans
        response = api_client.get("/api/bkapps/quota_plans/", {"app_code": bk_app.code})
        assert response.status_code == 200
        names = {item["name"] for item in response.data}
        assert public.name in names
        assert dedicated.name in names
        assert other.name not in names
