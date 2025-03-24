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

from typing import Dict, List, Optional
from urllib.parse import urlparse

import pytest
from django.conf import settings

from paas_wl.infras.cluster.loaders import DBConfigLoader, LegacyKubeConfigLoader
from paas_wl.infras.cluster.models import APIServer, Cluster

pytestmark = pytest.mark.django_db(databases=["workloads"])


@pytest.fixture(autouse=True)
def cluster_creator(ca_data, cert_data, key_data):
    def get_or_create(cluster_name: str, servers: List[Dict], token_value: Optional[str] = None):
        cluster = Cluster.objects.register_cluster(
            name=cluster_name,
            region=settings.DEFAULT_REGION_NAME,
            ca_data=ca_data,
            cert_data=cert_data,
            key_data=key_data,
            ingress_config={
                "app_root_domains": [{"name": "example.com"}],
                "sub_path_domains": [{"name": "example.com"}],
                "default_ingress_domain_tmpl": "%s.apps.com",
                "frontend_ingress_ip": "0.0.0.0",
                "port_map": {"http": "80", "https": "443"},
            },
            token_value=token_value,
        )

        for api_server in servers:
            APIServer.objects.update_or_create(
                host=api_server["host"], cluster=cluster, defaults={"tenant_id": cluster.tenant_id}
            )

    return get_or_create


class TestLoader:
    @pytest.fixture(autouse=True)
    def _setup(self, cluster_creator, clusters):
        Cluster.objects.all().delete()
        for cluster_name, attrs in clusters.items():
            cluster_creator(cluster_name, attrs["api_servers"])

    def test_get_all_cluster_names(self):
        loader = DBConfigLoader()
        assert len(loader.get_all_cluster_names()) == 3

    @pytest.mark.parametrize(
        ("context_name", "configurations_count", "server_hostname_set"),
        [
            ("foo", 1, {"hostname-of-foo"}),
            ("bar", 2, {"hostname-of-bar-a", "hostname-of-bar-b"}),
            ("baz", 2, {"192.168.1.100", "192.168.1.101"}),
        ],
    )
    def test_list_configurations_by_name(self, context_name, configurations_count, server_hostname_set):
        loader = DBConfigLoader()

        assert len(list(loader.list_configurations_by_name(context_name))) == configurations_count
        assert {
            urlparse(config.host).hostname for config in loader.list_configurations_by_name(context_name)
        } == server_hostname_set


class TestLoaderNoInitialClusters:
    @pytest.mark.parametrize(
        ("token_value", "auth_header_value"),
        [
            (None, None),
            ("foo_token", "Bearer foo_token"),
        ],
    )
    def test_auth_types(self, token_value, auth_header_value, cluster_creator):
        Cluster.objects.all().delete()
        api_servers = [{"host": "https://hostname-of-foo:6553"}]
        cluster_creator("default-cluster", api_servers, token_value=token_value)

        config = list(DBConfigLoader().list_configurations_by_name("default-cluster"))[0]
        assert config.api_key.get("authorization") == auth_header_value


class TestEnhancedKubeConfigLoader:
    """需要配合 assets/example-kube-config 进行测试"""

    def test_get_all_tags(self):
        loader = LegacyKubeConfigLoader.from_file("tests/paas_wl/assets/example-kube-config.yaml")
        assert len(loader.get_all_tags()) == 3

    @pytest.mark.parametrize(
        ("tag", "configurations_count", "server_hostname_set"),
        [
            ("foo", 1, {"hostname-of-foo"}),
            ("bar", 2, {"hostname-of-bar-a", "hostname-of-bar-b"}),
            ("baz", 2, {"hostname-of-baz-a", "hostname-of-baz-b"}),
        ],
    )
    def test_list_configurations_by_tag(self, tag, configurations_count, server_hostname_set):
        loader = LegacyKubeConfigLoader.from_file("tests/paas_wl/assets/example-kube-config.yaml")

        assert len(list(loader.list_configurations_by_tag(tag))) == configurations_count

        assert {
            urlparse(config.host).hostname for config in loader.list_configurations_by_tag(tag)
        } == server_hostname_set
