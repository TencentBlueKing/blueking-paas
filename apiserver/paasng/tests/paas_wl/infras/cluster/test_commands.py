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
import os

import pytest
from django.core.management import call_command
from django.utils.crypto import get_random_string

from paas_wl.infras.cluster.models import APIServer, Cluster

pytestmark = pytest.mark.django_db(databases=["workloads"])


@pytest.fixture()
def cluster_envs(monkeypatch):
    monkeypatch.setenv("PAAS_WL_CLUSTER_REGION", get_random_string(6))
    monkeypatch.setenv("PAAS_WL_CLUSTER_APP_ROOT_DOMAIN", "apps1.example.com")
    monkeypatch.setenv("PAAS_WL_CLUSTER_APP_ROOT_DOMAIN", "apps1.example.com")
    monkeypatch.setenv("PAAS_WL_CLUSTER_SUB_PATH_DOMAIN", "apps2.example.com")
    monkeypatch.setenv("PAAS_WL_CLUSTER_HTTP_PORT", "880")
    monkeypatch.setenv("PAAS_WL_CLUSTER_HTTPS_PORT", "8443")
    monkeypatch.setenv("PAAS_WL_CLUSTER_NODE_SELECTOR", "{\"dedicated\":\"bkSaas\"}")
    monkeypatch.setenv(
        "PAAS_WL_CLUSTER_TOLERATIONS",
        "[{\"effect\":\"NoSchedule\",\"key\":\"dedicated\",\"operator\":\"Equal\",\"value\":\"bkSaas\"}]",
    )
    monkeypatch.setenv(
        "PAAS_WL_CLUSTER_API_SERVER_URLS", "https://kubernetes.default.svc.cluster.localroot;https://10.0.0.1"
    )


@pytest.mark.parametrize(
    "https_enabled, expect",
    [
        ("true", True),
        ("false", False),
    ],
)
def test_init_cluster(cluster_envs, https_enabled, expect):
    os.environ["PAAS_WL_CLUSTER_ENABLED_HTTPS_BY_DEFAULT"] = https_enabled

    call_command("initial_default_cluster")

    cluster = Cluster.objects.get(name="default-main")

    ingress_config = cluster.ingress_config
    assert ingress_config.app_root_domains[0].https_enabled is expect
    assert ingress_config.sub_path_domains[0].https_enabled is expect
    assert ingress_config.app_root_domains[0].name == "apps1.example.com"
    assert ingress_config.sub_path_domains[0].name == "apps2.example.com"
    assert ingress_config.port_map.http == 880
    assert ingress_config.port_map.https == 8443
    assert cluster.default_tolerations == [
        {'effect': 'NoSchedule', 'key': 'dedicated', 'operator': 'Equal', 'value': 'bkSaas'}
    ]
    assert cluster.default_node_selector == {"dedicated": "bkSaas"}
    urls = APIServer.objects.filter(cluster=cluster).values_list("host", flat=True)
    assert set(urls) == {'https://kubernetes.default.svc.cluster.localroot', "https://10.0.0.1"}
