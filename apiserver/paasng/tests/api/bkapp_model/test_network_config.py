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

from paasng.platform.bkapp_model.models import DomainResolution, SvcDiscConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestSvcDiscConfigViewSet:
    @pytest.fixture()
    def svc_disc(self, bk_app):
        """创建一个 SvcDiscConfig 对象"""
        return SvcDiscConfig.objects.create(
            application=bk_app,
            bk_saas=[
                {
                    "bkAppCode": "bk_app_code_test",
                    "moduleName": "module_name_test",
                }
            ],
        )

    def test_get_normal(self, api_client, bk_app, svc_disc):
        url = f"/api/bkapps/applications/{bk_app.code}/svc_disc/"
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["bk_saas"] == [{"bk_app_code": "bk_app_code_test", "module_name": "module_name_test"}]

    def test_get_missing(self, api_client, bk_app):
        url = f"/api/bkapps/applications/{bk_app.code}/svc_disc/"
        response = api_client.get(url)
        assert response.status_code == 404

    def test_upsert_normal(self, api_client, bk_app, svc_disc):
        url = f"/api/bkapps/applications/{bk_app.code}/svc_disc/"
        request_body = {"bk_saas": [{"bk_app_code": bk_app.code, "module_name": "default"}]}
        response = api_client.post(url, request_body)
        assert response.status_code == 200
        assert response.data["bk_saas"] == [{"bk_app_code": bk_app.code, "module_name": "default"}]

    def test_upsert_module_absent(self, api_client, bk_app, svc_disc):
        url = f"/api/bkapps/applications/{bk_app.code}/svc_disc/"
        request_body = {"bk_saas": [{"bk_app_code": bk_app.code}]}
        response = api_client.post(url, request_body)
        assert response.status_code == 200
        assert response.data["bk_saas"] == [{"bk_app_code": bk_app.code, "module_name": None}]

    def test_upsert_invalid_module(self, api_client, bk_app, svc_disc):
        url = f"/api/bkapps/applications/{bk_app.code}/svc_disc/"
        request_body = {"bk_saas": [{"bk_app_code": bk_app.code, "module_name": "test-invalid-module-name"}]}
        response = api_client.post(url, request_body)
        assert response.status_code == 400

    def test_upsert_duplicated_entries(self, api_client, bk_app, svc_disc):
        url = f"/api/bkapps/applications/{bk_app.code}/svc_disc/"
        request_body = {
            "bk_saas": [
                # Duplicated entries
                {"bk_app_code": bk_app.code, "module_name": "default"},
                {"bk_app_code": bk_app.code, "module_name": "default"},
            ]
        }
        response = api_client.post(url, request_body)
        assert response.status_code == 400


class TestDomainResolutionViewSet:
    @pytest.fixture()
    def domain_resolution(self, bk_app):
        """创建一个 DomainResolution 对象"""
        return DomainResolution.objects.create(
            application=bk_app,
            nameservers=["192.168.1.1", "192.168.1.2"],
            host_aliases=[
                {
                    "ip": "bk_app_code_test",
                    "hostnames": [
                        "bk_app_code_test",
                        "bk_app_code_test_x",
                    ],
                }
            ],
        )

    def test_get(self, api_client, bk_app, domain_resolution):
        url = f"/api/bkapps/applications/{bk_app.code}/domain_resolution/"
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["nameservers"] == ["192.168.1.1", "192.168.1.2"]
        assert response.data["host_aliases"] == [
            {
                "ip": "bk_app_code_test",
                "hostnames": [
                    "bk_app_code_test",
                    "bk_app_code_test_x",
                ],
            }
        ]

    def test_get_error(self, api_client, bk_app):
        url = f"/api/bkapps/applications/{bk_app.code}/domain_resolution/"
        response = api_client.get(url)
        assert response.status_code == 404

    @pytest.mark.parametrize(
        ("request_body", "nameservers", "host_aliases"),
        [
            (
                {
                    "nameservers": ["192.168.1.3", "192.168.1.4"],
                    "host_aliases": [
                        {
                            "ip": "1.1.1.1",
                            "hostnames": [
                                "bk_app_code_test",
                                "bk_app_code_test_z",
                            ],
                        }
                    ],
                },
                ["192.168.1.3", "192.168.1.4"],
                [
                    {
                        "ip": "1.1.1.1",
                        "hostnames": [
                            "bk_app_code_test",
                            "bk_app_code_test_z",
                        ],
                    }
                ],
            ),
            (
                {
                    "nameservers": ["192.168.1.3", "192.168.1.4"],
                },
                ["192.168.1.3", "192.168.1.4"],
                [],
            ),
            (
                {
                    "host_aliases": [
                        {
                            "ip": "1.1.1.1",
                            "hostnames": [
                                "bk_app_code_test",
                                "bk_app_code_test_z",
                            ],
                        }
                    ],
                },
                [],
                [
                    {
                        "ip": "1.1.1.1",
                        "hostnames": [
                            "bk_app_code_test",
                            "bk_app_code_test_z",
                        ],
                    }
                ],
            ),
            (
                {
                    "nameservers": [],
                    "host_aliases": [],
                },
                [],
                [],
            ),
        ],
    )
    def test_upsert(self, api_client, bk_app, domain_resolution, request_body, nameservers, host_aliases):
        url = f"/api/bkapps/applications/{bk_app.code}/domain_resolution/"

        response = api_client.post(url, request_body)
        assert response.status_code == 200
        assert response.data["nameservers"] == nameservers or domain_resolution.nameservers
        assert response.data["host_aliases"] == host_aliases or domain_resolution.nameservers

    def test_upsert_error(self, api_client, bk_app, domain_resolution):
        url = f"/api/bkapps/applications/{bk_app.code}/domain_resolution/"

        response = api_client.post(url)
        assert response.status_code == 400
