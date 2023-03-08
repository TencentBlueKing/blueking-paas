# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from urllib.parse import urljoin

import pytest

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.parametrize(
    "request_path, original_path, x_script_name",
    [
        ("/", "/", "/"),
        ("/bar", "/bar", "/"),
        ("/bar/", "/bar/", "/"),
        ("/foo", "/", "/foo"),
        ("/foo/", "/", "/foo"),
        ("/foo/bar", "/bar", "/foo"),
        ("/foo/bar/baz/", "/bar/baz/", "/foo"),
        # 因为 /multi/layer 未匹配到 /multi/layer/, 因此流量转发到根路径
        ("/multi/layer", "/multi/layer", "/"),
        ("/multi/layer/", "/", "/multi/layer"),
        ("/multi/layer/foo", "/foo", "/multi/layer"),
        ("/multi/layer/foo/bar/", "/foo/bar/", "/multi/layer"),
    ],
)
def test_get(
    framework,
    echo_pod,
    echo_service,
    echo_ingress,
    echo_hostname,
    http_client,
    request_path,
    original_path,
    x_script_name,
):
    with framework.ensure_ingress(echo_ingress):
        base = f"http://{echo_hostname}"
        resp = http_client.get(urljoin(base, request_path))
        assert resp.status_code == 200
        data = resp.json()

        assert data["http"]["originalUrl"] == original_path
        assert data["request"]["params"]['0'] == original_path
        assert data["request"]["headers"]["host"] == echo_hostname
        assert data["request"]["headers"]["x-script-name"] == x_script_name


@pytest.mark.parametrize(
    "request_path, original_path, x_script_name",
    [
        ("/", "/", "/"),
        ("/bar", "/bar", "/"),
        ("/bar/", "/bar/", "/"),
        ("/foo", "/", "/foo"),
        ("/foo/", "/", "/foo"),
        ("/foo/bar", "/bar", "/foo"),
        ("/foo/bar/baz/", "/bar/baz/", "/foo"),
        # 因为 /multi/layer 未匹配到 /multi/layer/, 因此流量转发到根路径
        ("/multi/layer", "/multi/layer", "/"),
        ("/multi/layer/", "/", "/multi/layer"),
        ("/multi/layer/foo", "/foo", "/multi/layer"),
        ("/multi/layer/foo/bar/", "/foo/bar/", "/multi/layer"),
    ],
)
def test_post(
    framework,
    echo_pod,
    echo_service,
    echo_ingress,
    echo_hostname,
    http_client,
    request_path,
    original_path,
    x_script_name,
):
    with framework.ensure_ingress(echo_ingress):
        base = f"http://{echo_hostname}"
        resp = http_client.post(urljoin(base, request_path), json={"foo": "bar"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["http"]["originalUrl"] == original_path
        assert data["request"]["params"]['0'] == original_path
        assert data["request"]["body"] == {"foo": "bar"}
        assert data["request"]["headers"]["host"] == echo_hostname
        assert data["request"]["headers"]["x-script-name"] == x_script_name
