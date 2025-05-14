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

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestBCSResourceViewSet:
    @pytest.fixture(autouse=True)
    def _patch_bcs_api(self):
        with (
            patch(
                "paasng.infras.bcs.client.Client.api.list_auth_projects",
                return_value={
                    "code": 0,
                    "data": {
                        "total": 2,
                        "results": [
                            {
                                "projectID": "a9c54c3cb7854e3ea54499281f608c0b",
                                "projectCode": "blueking",
                                "name": "蓝鲸",
                                "description": "蓝鲸",
                                "isOffline": True,
                                "businessID": "100",
                                "businessName": "蓝鲸",
                            },
                            {
                                "projectID": "bb876f1246be4c079406d5992d1bf24c",
                                "projectCode": "blueking-paas",
                                "name": "蓝鲸 PaaS",
                                "description": "蓝鲸 PaaS",
                                "isOffline": False,
                                "businessID": "101",
                                "businessName": "蓝鲸 PaaS",
                            },
                        ],
                    },
                },
            ),
            patch(
                "paasng.infras.bcs.client.Client.api.list_project_clusters",
                return_value={
                    "code": 0,
                    "data": [
                        {
                            "clusterID": "BCS-K8S-00000",
                            "clusterName": "蓝鲸集群",
                            "environment": "prod",
                            "is_shared": False,
                        },
                        {
                            "clusterID": "BCS-K8S-20000",
                            "clusterName": "测试集群",
                            "environment": "debug",
                            "is_shared": False,
                        },
                        {
                            "clusterID": "BCS-K8S-40000",
                            "clusterName": "正式集群",
                            "environment": "prod",
                            "is_shared": False,
                        },
                        {
                            "clusterID": "BCS-K8S-49999",
                            "clusterName": "共享集群",
                            "environment": "prod",
                            "is_shared": True,
                        },
                    ],
                },
            ),
        ):
            yield

    def test_list_projects(self, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(reverse("plat_mgt.infras.bcs.project.list"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [
            {
                "id": "bb876f1246be4c079406d5992d1bf24c",
                "code": "blueking-paas",
                "name": "蓝鲸 PaaS",
                "description": "蓝鲸 PaaS",
                "biz_id": "101",
                "biz_name": "蓝鲸 PaaS",
            },
        ]

    def test_list_clusters(self, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.bcs.cluster.list",
                kwargs={"project_id": "bb876f1246be4c079406d5992d1bf24c"},
            )
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [
            {
                "id": "BCS-K8S-00000",
                "name": "蓝鲸集群",
                "environment": "prod",
            },
            {
                "id": "BCS-K8S-20000",
                "name": "测试集群",
                "environment": "debug",
            },
            {
                "id": "BCS-K8S-40000",
                "name": "正式集群",
                "environment": "prod",
            },
        ]
