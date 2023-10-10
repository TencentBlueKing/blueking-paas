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
import cattr
import pytest
from blue_krill.contextlib import nullcontext as does_not_raise
from django.db.utils import IntegrityError
from django.utils.crypto import get_random_string

from paas_wl.infras.cluster.constants import ClusterTokenType
from paas_wl.infras.cluster.exceptions import DuplicatedDefaultClusterError, NoDefaultClusterError, SwitchDefaultClusterError
from paas_wl.infras.cluster.models import Cluster, Domain, EnhancedConfiguration, IngressConfig, PortMap

pytestmark = pytest.mark.django_db(databases=["workloads"])


@pytest.fixture()
def region():
    return get_random_string()


@pytest.fixture
def default_cluster_creator(example_cluster_config):
    def creator(region: str):
        return Cluster.objects.register_cluster(
            region=region, name=get_random_string(), is_default=True, **example_cluster_config
        )

    return creator


class TestCluster:
    @pytest.mark.parametrize(
        "is_default, expectation",
        [
            (True, does_not_raise()),
            (False, pytest.raises(NoDefaultClusterError)),
        ],
    )
    def test_register(self, region, is_default, expectation, example_cluster_config):
        name = get_random_string()
        with expectation:
            Cluster.objects.register_cluster(region=region, name=name, is_default=is_default, **example_cluster_config)

    def test_use_register_cluster_to_change_default_cluster(
        self, region, default_cluster_creator, example_cluster_config
    ):
        cluster = default_cluster_creator(region=region)

        with pytest.raises(SwitchDefaultClusterError):
            Cluster.objects.register_cluster(
                region=region, name=cluster.name, is_default=False, **example_cluster_config
            )

    def test_register_duplicated_default_cluster(self, region, default_cluster_creator):
        default_cluster_creator(region)
        with pytest.raises(DuplicatedDefaultClusterError):
            default_cluster_creator(region)

    def test_register_duplicated_cluster_name(self, example_cluster_config):
        region1 = get_random_string()
        region2 = get_random_string()
        name = get_random_string()

        with pytest.raises(IntegrityError):
            Cluster.objects.register_cluster(region=region1, name=name, is_default=True, **example_cluster_config)
            Cluster.objects.register_cluster(region=region2, name=name, is_default=True, **example_cluster_config)

    @pytest.mark.parametrize(
        "name1, name2, target_cluster, expectation",
        [
            ("default-cluster", "custom-cluster", "default-cluster", pytest.raises(SwitchDefaultClusterError)),
            ("default-cluster", "custom-cluster", "custom-cluster", does_not_raise()),
        ],
    )
    def test_switch_default_cluster(self, region, example_cluster_config, name1, name2, target_cluster, expectation):
        Cluster.objects.register_cluster(region=region, name=name1, is_default=True, **example_cluster_config)
        Cluster.objects.register_cluster(region=region, name=name2, is_default=False, **example_cluster_config)

        with expectation:
            Cluster.objects.switch_default_cluster(region=region, cluster_name=target_cluster)

    def test_token(self, region, example_cluster_config):
        Cluster.objects.register_cluster(
            region=region, name='default-cluster', is_default=True, token_value='foo_token', **example_cluster_config
        )
        cluster = Cluster.objects.get(name='default-cluster')
        assert cluster.token_type == ClusterTokenType.SERVICE_ACCOUNT
        assert cluster.token_value == 'foo_token'


class TestIngressConfigField:
    def test_port_map(self, region):
        ingress_config = {
            "port_map": {"http": "81", "https": "8081"},
        }
        c: Cluster = Cluster.objects.create(region=region, name='dft', is_default=True, ingress_config=ingress_config)
        c.refresh_from_db()
        assert isinstance(c.ingress_config, IngressConfig)
        assert isinstance(c.ingress_config.port_map, PortMap)
        assert c.ingress_config.port_map.http == 81
        assert c.ingress_config.port_map.get_port_num('https') == 8081

        # Update `PortMap` to None value
        c.ingress_config = {}  # type: ignore
        c.save()
        c.refresh_from_db()
        assert isinstance(c.ingress_config.port_map, PortMap)
        assert c.ingress_config.port_map.http == 80
        assert c.ingress_config.port_map.get_port_num('https') == 443

    def test_domains(self, region):
        ingress_config = {"app_root_domains": ["foo.com", {"name": "bar.com"}, {"name": "baz.com", "reserved": True}]}
        c: Cluster = Cluster.objects.create(region=region, name='dft', is_default=True, ingress_config=ingress_config)
        c.refresh_from_db()
        assert isinstance(c.ingress_config, IngressConfig)
        assert len(c.ingress_config.app_root_domains) == 3
        assert all(isinstance(domain, Domain) for domain in c.ingress_config.app_root_domains)

        assert c.ingress_config.app_root_domains[0].name == "foo.com"
        assert c.ingress_config.app_root_domains[0].reserved is False
        assert c.ingress_config.app_root_domains[1].name == "bar.com"
        assert c.ingress_config.app_root_domains[1].reserved is False
        assert c.ingress_config.app_root_domains[2].name == "baz.com"
        assert c.ingress_config.app_root_domains[2].reserved is True

    def test_find_app_root_domain(self):
        d = {
            "app_root_domains": [
                {"name": "bar.example.com"},
                {"name": "foo.example.com", "reserved": True},
            ]
        }
        config = cattr.structure(d, IngressConfig)
        root_domain = config.find_app_root_domain('test.foo.example.com')
        assert root_domain is not None
        assert root_domain.name == 'foo.example.com'
        assert root_domain.reserved is True

        assert config.find_app_root_domain('test.foo.example.org') is None


class TestEnhancedConfiguration:
    def test_create_normal(self):
        conf = EnhancedConfiguration.create('https://192.168.1.1:8443', '', '', '', '', '')
        assert conf.host == 'https://192.168.1.1:8443'
        assert conf.resolver_records == {}

    def test_create_force_hostname(self):
        conf = EnhancedConfiguration.create('https://192.168.1.1:8443', 'kubernetes', '', '', '', '')
        assert conf.host == 'https://kubernetes:8443'
        assert conf.resolver_records == {'kubernetes': '192.168.1.1'}

    def test_create_invalid_values(self):
        with pytest.raises(ValueError):
            EnhancedConfiguration.create('https://example.com', 'kubernetes', '', '', '', '')

    @pytest.mark.parametrize(
        'host,ip',
        [
            ('https://192.168.1.100/', '192.168.1.100'),
            ('http://192.168.1.1:8080/', '192.168.1.1'),
            ('http://[fdf8:f53b:82e4::53]:8443/', 'fdf8:f53b:82e4::53'),
            ('http://[fdf8:f53b:82e4::53]/', 'fdf8:f53b:82e4::53'),
            ('https://kubernetes:8443/', None),
        ],
    )
    def test_extract_ip(self, host, ip):
        assert EnhancedConfiguration.extract_ip(host) == ip
