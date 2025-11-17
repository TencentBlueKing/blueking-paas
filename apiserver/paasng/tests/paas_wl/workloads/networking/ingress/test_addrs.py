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
from django.test import override_settings

from paas_wl.infras.cluster.entities import Domain as ClusterDomain
from paas_wl.infras.cluster.entities import PortMap
from paas_wl.workloads.networking.entrance.addrs import Address, AddressType
from paas_wl.workloads.networking.entrance.shim import LiveEnvAddresses, PreAllocatedEnvAddresses
from paas_wl.workloads.networking.ingress.constants import AppDomainSource, AppSubpathSource
from paas_wl.workloads.networking.ingress.models import AppDomain, AppSubpath, Domain
from tests.paas_wl.utils.release import create_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestEnvAddresses:
    @pytest.fixture(autouse=True)
    def _setup_data(self, bk_module, bk_stag_env, bk_stag_wl_app):
        wl_app = bk_stag_wl_app
        # Create all types of domains
        # source type: subdomain
        AppDomain.objects.create(app=wl_app, host="foo.example.com", source=AppDomainSource.AUTO_GEN)
        AppDomain.objects.create(app=wl_app, host="foo-more.example.org", source=AppDomainSource.AUTO_GEN)
        AppDomain.objects.create(app=wl_app, host="foo.example.org", source=AppDomainSource.AUTO_GEN)
        # source type: subpath
        AppSubpath.objects.create(app=wl_app, subpath="/foo/", source=AppSubpathSource.DEFAULT)
        # source type: custom
        Domain.objects.create(
            name="foo-custom.example.com", path_prefix="/", module_id=bk_module.id, environment_id=bk_stag_env.id
        )

    def test_not_deployed(self, bk_stag_env):
        # 未部署, LiveEnvAddresses.list 为空
        assert LiveEnvAddresses(bk_stag_env).list() == []
        # 但 LiveEnvAddresses.list_subdomain 不为空, 因为读取的是 AppDomain 模型
        assert LiveEnvAddresses(bk_stag_env).list_subdomain() == [
            Address(type=AddressType.SUBDOMAIN, url="http://foo.example.com/"),
            Address(type=AddressType.SUBDOMAIN, url="http://foo.example.org/"),
            Address(type=AddressType.SUBDOMAIN, url="http://foo-more.example.org/"),
        ]

        # 短域名在前
        subdomain = PreAllocatedEnvAddresses(bk_stag_env).list_subdomain()
        assert len(subdomain) > 1
        assert len(subdomain[0].url) < len(subdomain[1].url)

    def test_pre_allocated_with_reserved(self, bk_stag_env, patch_ingress_config):
        patch_ingress_config(
            app_root_domains=[
                ClusterDomain(name="foo-p0.example.com", reserved=True),
                ClusterDomain(name="foo-p10.example.com", reserved=False),
            ],
            sub_path_domains=[
                ClusterDomain(name="foo-p0.example.com", https_enabled=True, reserved=True),
                ClusterDomain(name="foo-p20.example.com", https_enabled=False),
            ],
            port_map=PortMap(http=8080, https=443),
        )

        # 非保留的域名在前
        subdomains = PreAllocatedEnvAddresses(bk_stag_env).list_subdomain()
        assert len(subdomains) == 4
        assert len(subdomains[0].url) > len(subdomains[2].url)

        assert "foo-p10" in subdomains[0].url
        assert subdomains[0].is_sys_reserved is False

        assert "foo-p0" in subdomains[2].url
        assert subdomains[2].is_sys_reserved is True

        with override_settings(USE_LEGACY_SUB_PATH_PATTERN=True):
            subpaths = PreAllocatedEnvAddresses(bk_stag_env).list_subpath()
            assert len(subpaths) == 6
            assert len(subpaths[0].url) > len(subpaths[3].url)

            assert "foo-p20" in subpaths[0].url
            assert subpaths[0].is_sys_reserved is False

            assert "foo-p0" in subpaths[3].url
            assert subpaths[3].is_sys_reserved is True

    def test_integrated(self, bk_user, bk_stag_env, patch_ingress_config):
        """Integrated test with multiple subpath domains and customized ports"""
        patch_ingress_config(
            app_root_domains=[
                ClusterDomain(name="foo.example.com", reserved=True),
            ],
            sub_path_domains=[
                ClusterDomain(name="p1.example.com", https_enabled=True, reserved=True),
                ClusterDomain(name="p2.example.com", https_enabled=False),
            ],
            port_map=PortMap(http=8080, https=443),
        )

        # Create a successful release record to by-paas deployment check
        create_release(bk_stag_env.wl_app, bk_user, failed=False)
        addrs = LiveEnvAddresses(bk_stag_env).list()
        assert addrs == [
            Address(AddressType.SUBDOMAIN, "http://foo.example.org:8080/", False),
            Address(AddressType.SUBDOMAIN, "http://foo-more.example.org:8080/", False),
            Address(AddressType.SUBDOMAIN, "http://foo.example.com:8080/", True),
            Address(AddressType.SUBPATH, "http://p2.example.com:8080/foo/", False),
            Address(AddressType.SUBPATH, "https://p1.example.com/foo/", True),
            Address(
                AddressType.CUSTOM,
                "http://foo-custom.example.com:8080/",
                False,
                id=Domain.objects.get(environment_id=bk_stag_env.id).id,
            ),
        ]
