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

import cattr
import pytest

from paas_wl.infras.cluster.entities import Domain, IngressConfig, PortMap
from paas_wl.infras.cluster.models import Cluster

pytestmark = pytest.mark.django_db(databases=["workloads"])


class TestIngressConfigField:
    def test_port_map(self):
        ingress_config = {
            "port_map": {"http": "81", "https": "8081"},
        }
        c: Cluster = Cluster.objects.create(name="dft", ingress_config=ingress_config)
        c.refresh_from_db()
        assert isinstance(c.ingress_config, IngressConfig)
        assert isinstance(c.ingress_config.port_map, PortMap)
        assert c.ingress_config.port_map.http == 81
        assert c.ingress_config.port_map.get_port_num("https") == 8081

        # Update `PortMap` to None value
        c.ingress_config = {}  # type: ignore
        c.save()
        c.refresh_from_db()
        assert isinstance(c.ingress_config.port_map, PortMap)
        assert c.ingress_config.port_map.http == 80
        assert c.ingress_config.port_map.get_port_num("https") == 443

    def test_domains(self):
        ingress_config = {"app_root_domains": ["foo.com", {"name": "bar.com"}, {"name": "baz.com", "reserved": True}]}
        c: Cluster = Cluster.objects.create(name="dft", ingress_config=ingress_config)
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
        root_domain = config.find_app_root_domain("test.foo.example.com")
        assert root_domain is not None
        assert root_domain.name == "foo.example.com"
        assert root_domain.reserved is True

        assert config.find_app_root_domain("test.foo.example.org") is None
