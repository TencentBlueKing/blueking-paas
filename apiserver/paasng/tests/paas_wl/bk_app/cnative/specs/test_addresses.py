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

from paas_wl.bk_app.cnative.specs.addresses import AddrResourceManager, save_addresses, to_domain, to_shared_tls_domain
from paas_wl.bk_app.cnative.specs.addresses import Domain as MappingDomain
from paas_wl.workloads.networking.ingress.constants import AppDomainProtocol, AppDomainSource, AppSubpathSource
from paas_wl.workloads.networking.ingress.models import AppDomain, AppDomainSharedCert, AppSubpath, Domain
from paasng.platform.modules.constants import ExposedURLType
from tests.utils.mocks.cluster import cluster_ingress_config

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class Test__save_addresses:
    @pytest.mark.parametrize(
        ("protocol", "expected_app_domain_count", "expected_sub_path_count"),
        [(AppDomainProtocol.HTTP, 3 * 2, 3), (AppDomainProtocol.GRPC, 3 * 2, 0)],
    )
    def test(
        self,
        bk_module,
        bk_prod_env,
        bk_prod_wl_app,
        settings,
        protocol,
        expected_app_domain_count,
        expected_sub_path_count,
    ):
        settings.USE_LEGACY_SUB_PATH_PATTERN = False
        bk_module.exposed_url_type = ExposedURLType.SUBDOMAIN.value
        bk_module.save(update_fields=["exposed_url_type"])

        assert AppDomain.objects.filter(app=bk_prod_wl_app).count() == 0
        assert AppSubpath.objects.filter(app=bk_prod_wl_app).count() == 0

        with cluster_ingress_config(
            replaced_config={
                "sub_path_domains": [{"name": "sub.example.com"}, {"name": "sub.example.cn"}],
                "app_root_domains": [{"name": "bkapps.example.com"}, {"name": "bkapps.example2.com"}],
            }
        ):
            save_addresses(bk_prod_env, protocol)

        assert AppDomain.objects.filter(app=bk_prod_wl_app).count() == expected_app_domain_count
        assert AppSubpath.objects.filter(app=bk_prod_wl_app).count() == expected_sub_path_count


@pytest.mark.auto_create_ns()
class TestToDomain:
    @pytest.mark.parametrize(
        ("host", "https_enabled", "secret_name_has_value"),
        [
            ("x-foo.example.com", False, False),
            ("not-match.example.com", True, False),
            ("x-foo.example.com", True, True),
        ],
    )
    def test_with_https(self, host, https_enabled, secret_name_has_value, bk_stag_wl_app):
        # Create a shared cert object
        AppDomainSharedCert.objects.create(
            tenant_id=bk_stag_wl_app.tenant_id,
            name="foo",
            cert_data="",
            key_data="",
            auto_match_cns="*-foo.example.com",
        )
        d = AppDomain.objects.create(
            app=bk_stag_wl_app,
            host=host,
            source=AppDomainSource.AUTO_GEN,
            https_enabled=https_enabled,
        )

        domain = to_domain(d)
        if secret_name_has_value:
            assert domain.tlsSecretName is not None
            assert len(domain.tlsSecretName) > 0
        else:
            assert domain.tlsSecretName is None


@pytest.mark.auto_create_ns()
class TestToSharedTLSDomain:
    def test_normal(self, bk_stag_wl_app):
        d = MappingDomain(host="x-foo.example.com", pathPrefixList=["/"])
        d = to_shared_tls_domain(d, bk_stag_wl_app)
        assert d.tlsSecretName is None

        # Create a shared cert object
        AppDomainSharedCert.objects.create(
            tenant_id=bk_stag_wl_app.tenant_id,
            name="foo",
            cert_data="",
            key_data="",
            auto_match_cns="*-foo.example.com",
        )
        d = to_shared_tls_domain(d, bk_stag_wl_app)
        assert d.tlsSecretName is not None
        assert len(d.tlsSecretName) > 0


class TestAddrResourceManager:
    def test_integrated(self, bk_module, bk_stag_env, bk_stag_wl_app):
        # Create all types of domains
        # source type: subdomain
        AppDomain.objects.create(app=bk_stag_wl_app, host="foo-subdomain.example.com", source=AppDomainSource.AUTO_GEN)
        # source type: subpath
        AppSubpath.objects.create(app=bk_stag_wl_app, subpath="/foo-subpath/", source=AppSubpathSource.DEFAULT)
        # source type: custom
        Domain.objects.create(
            name="foo-custom.example.com", path_prefix="/", module_id=bk_module.id, environment_id=bk_stag_env.id
        )

        addr_mgr = AddrResourceManager(bk_stag_env)
        mapping = addr_mgr.build_mapping()
        assert len(mapping.spec.data) == 3

        # Remove all types of domains
        AppDomain.objects.all().delete()
        AppSubpath.objects.all().delete()
        Domain.objects.all().delete()
        mapping = addr_mgr.build_mapping()
        assert len(mapping.spec.data) == 0
