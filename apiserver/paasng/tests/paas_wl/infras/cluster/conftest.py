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
import base64
from textwrap import dedent

import pytest

from paas_wl.infras.cluster.constants import ClusterFeatureFlag, ClusterType


@pytest.fixture
def example_cluster_config():
    return {
        'ingress_config': {
            "app_root_domains": [{"name": "example.com"}],
            "sub_path_domains": [{"name": "example.com"}],
            "default_ingress_domain_tmpl": "%s.apps.com",
            "frontend_ingress_ip": "0.0.0.0",
            "port_map": {"http": "80", "https": "443"},
        },
        'ca_data': '',
        'cert_data': '',
        'key_data': '',
        'feature_flags': ClusterFeatureFlag.get_default_flags_by_cluster_type(ClusterType.NORMAL),
    }


@pytest.fixture()
def clusters():
    return {
        "foo": {
            "api_servers": [
                dict(
                    host="https://hostname-of-foo:6553",
                )
            ]
        },
        "bar": {
            "api_servers": [
                dict(
                    host="https://hostname-of-bar-a:6553",
                ),
                dict(
                    host="https://hostname-of-bar-b:6553",
                ),
            ]
        },
        "baz": {
            "api_servers": [
                dict(host="https://192.168.1.100:6553", overridden_hostname="baz-a.domain.com"),
                dict(host="https://192.168.1.101:6553", overridden_hostname="baz-b.domain.com"),
            ]
        },
    }


@pytest.fixture
def ca_data() -> str:
    return base64.b64encode(
        dedent(
            """-----BEGIN CERTIFICATE-----
            -----END CERTIFICATE-----
            """
        ).encode()
    ).decode()


@pytest.fixture
def cert_data() -> str:
    return base64.b64encode(
        dedent(
            """-----BEGIN CERTIFICATE-----
            -----END CERTIFICATE-----"""
        ).encode()
    ).decode()


@pytest.fixture
def key_data() -> str:
    return base64.b64encode(
        dedent(
            """-----BEGIN RSA PRIVATE KEY-----
            -----END RSA PRIVATE KEY-----"""
        ).encode()
    ).decode()
