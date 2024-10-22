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

from paasng.platform.applications.models import Application
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(autouse=True)
def bk_app2() -> Application:
    """Create another application for testing"""
    return create_app()


class TestSvcDiscConfigViewSet:
    @pytest.fixture()
    def test_url(self, bk_app) -> str:
        return reverse("api.applications.svc_disc", kwargs={"code": bk_app.code})

    @pytest.fixture()
    def with_default_disc(self, api_client, test_url, bk_app2):
        """Create a default svc_disc object"""
        resp = api_client.post(test_url, {"bk_saas": [{"bk_app_code": bk_app2.code, "module_name": "default"}]})
        return resp

    def test_get_missing(self, api_client, test_url):
        response = api_client.get(test_url)

        assert response.status_code == 404

    def test_get_normal(self, with_default_disc, api_client, bk_app2, test_url):
        response = api_client.get(test_url)

        assert response.status_code == 200
        assert response.data["bk_saas"] == [{"bk_app_code": bk_app2.code, "module_name": "default"}]

    def test_upsert_normal(self, with_default_disc, api_client, bk_app, test_url):
        response = api_client.post(test_url, {"bk_saas": [{"bk_app_code": bk_app.code, "module_name": "default"}]})

        assert response.status_code == 200
        assert response.data["bk_saas"] == [{"bk_app_code": bk_app.code, "module_name": "default"}]

    def test_upsert_module_absent(self, api_client, bk_app, test_url):
        response = api_client.post(test_url, {"bk_saas": [{"bk_app_code": bk_app.code}]})

        assert response.status_code == 200
        assert response.data["bk_saas"] == [{"bk_app_code": bk_app.code, "module_name": None}]

    def test_upsert_invalid_module(self, api_client, bk_app, test_url):
        response = api_client.post(
            test_url, {"bk_saas": [{"bk_app_code": bk_app.code, "module_name": "test-invalid-module-name"}]}
        )

        assert response.status_code == 400

    def test_upsert_duplicated_entries(self, api_client, bk_app, test_url):
        response = api_client.post(
            test_url,
            {
                "bk_saas": [
                    # Duplicated entries
                    {"bk_app_code": bk_app.code, "module_name": "default"},
                    {"bk_app_code": bk_app.code, "module_name": "default"},
                ]
            },
        )

        assert response.status_code == 400


class TestDomainResolutionViewSet:
    @pytest.fixture()
    def test_url(self, bk_app) -> str:
        return reverse("api.applications.domain_resolution", kwargs={"code": bk_app.code})

    @pytest.fixture()
    def with_default_res(self, api_client, test_url):
        """创建一个默认的 DomainResolution 对象"""
        body = {
            "nameservers": ["192.168.1.1", "192.168.1.2"],
            "host_aliases": [
                {
                    "ip": "127.0.0.1",
                    "hostnames": [
                        "foo.example.com",
                        "foo2.example.com",
                    ],
                }
            ],
        }
        resp = api_client.post(test_url, body)
        return resp

    def test_get_missing(self, api_client, test_url):
        response = api_client.get(test_url)

        assert response.status_code == 404

    def test_get(self, with_default_res, api_client, bk_app, test_url):
        response = api_client.get(test_url)

        assert response.status_code == 200
        assert response.data["nameservers"] == ["192.168.1.1", "192.168.1.2"]
        assert response.data["host_aliases"] == [
            {
                "ip": "127.0.0.1",
                "hostnames": [
                    "foo.example.com",
                    "foo2.example.com",
                ],
            }
        ]

    @pytest.mark.parametrize(
        "req_body",
        [
            {
                "nameservers": ["192.168.1.100"],
                "host_aliases": [{"ip": "8.8.8.8", "hostnames": ["bar.example.com"]}],
            },
            # Only provide "nameserver"
            {
                "nameservers": ["192.168.1.100"],
            },
            # Only provide "host_aliases"
            {
                "host_aliases": [{"ip": "8.8.8.8", "hostnames": ["bar.example.com"]}],
            },
            # All fields are empty
            {
                "nameservers": [],
                "host_aliases": [],
            },
        ],
    )
    def test_upsert(self, with_default_res, api_client, test_url, req_body):
        old_ns = with_default_res.data["nameservers"]
        old_ha = with_default_res.data["host_aliases"]

        response = api_client.post(test_url, req_body)

        assert response.status_code == 200
        # When the field is missing in the body, the old value should be kept
        assert response.data["nameservers"] == req_body.get("nameservers") or old_ns
        assert response.data["host_aliases"] == req_body.get("host_aliases") or old_ha

    def test_upsert_no_data(self, with_default_res, api_client, test_url):
        response = api_client.post(test_url)

        assert response.status_code == 400
