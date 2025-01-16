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

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status


class TestBCSResourceViewSet:
    @pytest.fixture(autouse=True)
    def _patch_bcs_api(self):
        with patch(
            "paasng.infras.bk_user.client.Client.api.list_tenants",
            return_value={
                "data": [
                    {
                        "id": "system",
                        "name": "运营租户",
                        "status": "enabled",
                    },
                    {
                        "id": "blueking",
                        "name": "蓝鲸",
                        "status": "enabled",
                    },
                    {
                        "id": "legacy",
                        "name": "存量",
                        "status": "disabled",
                    },
                ],
            },
        ):
            yield

    def test_list_tenants(self, api_client):
        resp = api_client.get(reverse("api.tenant.list"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 3
