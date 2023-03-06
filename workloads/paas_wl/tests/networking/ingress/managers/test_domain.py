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
from unittest.mock import patch

import pytest
from django_dynamic_fixture import G

from paas_wl.networking.ingress.certs.utils import DomainWithCert
from paas_wl.networking.ingress.constants import AppDomainSource
from paas_wl.networking.ingress.entities.ingress import ingress_kmodel
from paas_wl.networking.ingress.exceptions import DefaultServiceNameRequired, EmptyAppIngressError, ValidCertNotFound
from paas_wl.networking.ingress.managers.domain import (
    CustomDomainIngressMgr,
    IngressDomainFactory,
    SubdomainAppIngressMgr,
    assign_custom_hosts,
)
from paas_wl.networking.ingress.models import AppDomain, AppDomainCert, AppDomainSharedCert, AutoGenDomain, Domain
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from tests.utils.app import create_app

pytestmark = [pytest.mark.django_db]


@pytest.mark.auto_create_ns
class TestAssignDomains:
    @pytest.fixture()
    def foo_shared_cert(self, app):
        AppDomainSharedCert.objects.create(
            region=app.region, name="foo", cert_data="", key_data="", auto_match_cns="*.foo.com"
        )

    @pytest.mark.parametrize(
        "domains",
        (
            [AutoGenDomain('foo.com'), AutoGenDomain('bar.com')],
            [AutoGenDomain('foo.com'), AutoGenDomain('www.foo.com')],
            [AutoGenDomain('foo.com'), AutoGenDomain('www.foo.com', https_enabled=True)],
        ),
    )
    def test_brand_new_domains(self, app, foo_shared_cert, domains):
        assign_custom_hosts(app, domains, 'foo-service')

        ingress_mgr = SubdomainAppIngressMgr(app)
        ingress = ingress_mgr.get()

        assert len(ingress.domains) == len(domains)
        assert {d.host for d in domains} == {d.host for d in ingress.domains}

    @pytest.mark.parametrize(
        "hostnames, domains_https_enabled",
        (
            (['www.foo.com', 'bar.com'], [True, False]),
            (['www.foo.com', 'bar.foo.com'], [True, True]),
        ),
    )
    def test_create_https_domains(self, app, foo_shared_cert, hostnames, domains_https_enabled):
        domains = [AutoGenDomain(hostname, https_enabled=True) for hostname in hostnames]
        assign_custom_hosts(app, domains, default_service_name='foo-service')
        domain_count = len(domains)
        ingress = SubdomainAppIngressMgr(app).get()

        assert [d.tls_enabled for d in ingress.domains] == domains_https_enabled
        assert AppDomain.objects.count() == domain_count

    def test_domain_transfer_partially(self, app, namespace_maker):
        domains_app1 = [AutoGenDomain('foo.com'), AutoGenDomain('bar.com')]
        assign_custom_hosts(app, domains_app1, 'foo-service')
        app_2 = create_app()
        namespace_maker.make(app_2.namespace)

        # Transfer "bar.com" to app_2
        domains_app1 = [
            AutoGenDomain('bar.com'),
            AutoGenDomain('app-2.com'),
        ]
        assign_custom_hosts(app_2, domains_app1, 'foo-service')

        ingress = SubdomainAppIngressMgr(app).get()
        assert len(ingress.domains) == 1
        hosts = [d.host for d in ingress.domains]
        assert 'foo.com' in hosts
        assert 'bar.com' not in hosts

        ingress = SubdomainAppIngressMgr(app_2).get()
        assert len(ingress.domains) == 2
        hosts = [d.host for d in ingress.domains]
        assert 'bar.com' in hosts
        assert 'app-2.com' in hosts

    def test_domain_transfer_fully(self, app, namespace_maker):
        domains = [AutoGenDomain('foo.com')]
        assign_custom_hosts(app, domains, 'foo-service')

        # Transfer all domains to app_2
        app_2 = create_app()
        namespace_maker.make(app_2.namespace)
        assign_custom_hosts(app_2, domains, 'foo-service')

        with pytest.raises(AppEntityNotFound):
            SubdomainAppIngressMgr(app).get()

        ingress = SubdomainAppIngressMgr(app_2).get()
        assert len(ingress.domains) == 1
        assert [d.host for d in ingress.domains] == ['foo.com']


@pytest.mark.auto_create_ns
class TestSubdomainAppIngressMgrCommon:
    """Test common interfaces for `SubdomainAppIngressMgr`"""

    @pytest.fixture(autouse=True)
    def _setup_data(self, app):
        AppDomain.objects.create(app=app, region=app.region, host='bar-2.com', source=AppDomainSource.AUTO_GEN)

    def test_sync_no_domains(self, app):
        AppDomain.objects.filter(app=app).delete()
        with pytest.raises(EmptyAppIngressError):
            ingress_mgr = SubdomainAppIngressMgr(app)
            ingress_mgr.sync(default_service_name='foo')

    def test_sync_creation_with_no_default_server_name(self, app):
        ingress_mgr = SubdomainAppIngressMgr(app)
        with pytest.raises(DefaultServiceNameRequired):
            ingress_mgr.sync()

    def test_sync_creation(self, app):
        ingresses = ingress_kmodel.list_by_app(app)
        assert len(ingresses) == 0

        ingress_mgr = SubdomainAppIngressMgr(app)
        ingress_mgr.sync(default_service_name='foo')
        ingresses = ingress_kmodel.list_by_app(app)

        assert len(ingresses) == 1
        ingress = ingresses[0]
        assert len(ingress.domains) > 0

    def test_sync_update(self, app):
        ingress_mgr = SubdomainAppIngressMgr(app)
        ingress_mgr.sync(default_service_name='foo')
        ingress_name = ingress_mgr.ingress_name
        assert len(ingress_kmodel.get(app, ingress_name).domains) == 1

        # Add an extra domain
        config = app.latest_config
        config.domain = 'bar.com'
        config.save()
        ingress_mgr.sync()

        assert len(ingress_kmodel.get(app, ingress_name).domains) == 2

    def test_delete_non_existed(self, app):
        ingress_mgr = SubdomainAppIngressMgr(app)
        ingress_mgr.delete()

    def test_integrated(self, app):
        ingress_mgr = SubdomainAppIngressMgr(app)
        ingress_mgr.sync(default_service_name='foo')
        assert len(ingress_kmodel.list_by_app(app)) == 1

        ingress_mgr.delete()
        assert len(ingress_kmodel.list_by_app(app)) == 0

    def test_update_target(self, app):
        ingress_mgr = SubdomainAppIngressMgr(app)
        ingress_mgr.sync(default_service_name='foo')
        ingress_mgr.update_target('foo-service', 'foo-port')

        ingress = ingress_kmodel.get(app, ingress_mgr.ingress_name)
        assert ingress.service_name == 'foo-service'
        assert ingress.service_port_name == 'foo-port'

    @pytest.mark.parametrize(
        'rewrite_to_root,expected_ret',
        [
            (True, True),
            (False, False),
        ],
    )
    def test_rewrite_ingress_path_to_root(self, rewrite_to_root, expected_ret, app):
        with patch.object(SubdomainAppIngressMgr, 'rewrite_ingress_path_to_root', new=rewrite_to_root):
            SubdomainAppIngressMgr(app).sync(default_service_name='foo')
            assert ingress_kmodel.list_by_app(app)[0].rewrite_to_root is expected_ret


class TestSubdomainAppIngressMgr:
    def test_list_desired_domains(self, app):
        ingress_mgr = SubdomainAppIngressMgr(app)
        domains = ingress_mgr.list_desired_domains()
        assert len(domains) == 0

    def test_list_desired_domains_with_extra(self, app):
        config = app.latest_config
        config.domain = 'bar.com'
        config.save()

        ingress_mgr = SubdomainAppIngressMgr(app)
        assert len(ingress_mgr.list_desired_domains()) == 1

        AppDomain.objects.create(app=app, region=app.region, host='bar-2.com', source=AppDomainSource.AUTO_GEN)
        assert len(ingress_mgr.list_desired_domains()) == 2

    def test_list_desired_domains_with_wrong_source(self, app):
        ingress_mgr = SubdomainAppIngressMgr(app)
        assert len(ingress_mgr.list_desired_domains()) == 0
        # SubDomain ingress should only include domains when their source is "CUSTOM"
        AppDomain.objects.create(app=app, region=app.region, host='foo.com', source=AppDomainSource.INDEPENDENT)
        assert len(ingress_mgr.list_desired_domains()) == 0


@pytest.mark.mock_get_structured_app
@pytest.mark.auto_create_ns
class TestCustomDomainIngressMgr:
    @pytest.mark.parametrize(
        'path_prefix,expected_path_prefixes,customized_ingress_name',
        [
            ('/', ['/'], False),
            ('/foo/', ['/foo/'], True),
        ],
    )
    def test_create(self, path_prefix, expected_path_prefixes, customized_ingress_name, bk_stag_env, bk_stag_wl_app):
        domain = G(
            Domain,
            name='foo.example.com',
            path_prefix=path_prefix,
            module_id=bk_stag_env.module.id,
            environment_id=bk_stag_env.id,
        )
        mgr = CustomDomainIngressMgr(domain)

        mgr.sync(default_service_name=bk_stag_wl_app.name)
        obj = ingress_kmodel.get(bk_stag_wl_app, mgr.make_ingress_name())

        if customized_ingress_name:
            assert obj.name == f"custom-foo.example.com-{domain.id}"
        else:
            assert obj.name == "custom-foo.example.com"
        assert obj.domains[0].path_prefix_list == expected_path_prefixes
        assert obj.service_name == bk_stag_wl_app.name
        mgr.delete()

    def test_normal_delete(self, bk_stag_env, bk_stag_wl_app):
        domain = G(
            Domain,
            name='foo.example.com',
            module_id=bk_stag_env.module.id,
            environment_id=bk_stag_env.id,
        )
        mgr = CustomDomainIngressMgr(domain)
        mgr.sync(default_service_name=bk_stag_wl_app.name)
        _ = ingress_kmodel.get(bk_stag_wl_app, mgr.make_ingress_name())
        mgr.delete()
        with pytest.raises(AppEntityNotFound):
            ingress_kmodel.get(bk_stag_wl_app, mgr.make_ingress_name())


@pytest.mark.auto_create_ns
class TestIntegratedDomains:
    """Test cases for some combined situations"""

    def test_assign_custom_hosts_affects_no_independent_domains(self, app):
        AppDomain.objects.create(
            app=app, region=app.region, host='foo-independent.com', source=AppDomainSource.INDEPENDENT
        )
        assert AppDomain.objects.filter(host='foo-independent.com').exists()
        assign_custom_hosts(app, [AutoGenDomain('foo.com')], 'foo-service')

        # Calling assign_custom_hosts should not remove AppDomain objects with source other than "CUSTOM"
        assert AppDomain.objects.filter(host='foo-independent.com').exists()


class TestIngressDomainFactory:
    def test_make_ingress_domain_with_http(self, app):
        domain_with_cert = DomainWithCert(host="example.com", path_prefix="", https_enabled=False)
        factory = IngressDomainFactory(app)
        domain = factory.create(domain_with_cert)
        assert domain.host == domain_with_cert.host
        assert domain.tls_enabled == domain_with_cert.https_enabled
        assert domain.tls_secret_name == ''

    def test_https_cert_not_found(self, app):
        domain_with_cert = DomainWithCert(host="example.com", path_prefix="", https_enabled=True)
        factory = IngressDomainFactory(app)
        with pytest.raises(ValidCertNotFound):
            factory.create(domain_with_cert)

    def test_https_cert_not_found_no_exception(self, app):
        domain_with_cert = DomainWithCert(host="example.com", path_prefix="", https_enabled=True)
        factory = IngressDomainFactory(app)
        domain = factory.create(domain_with_cert, raise_on_no_cert=False)
        assert domain.tls_enabled is False

    @pytest.mark.auto_create_ns
    @pytest.mark.parametrize(
        "cert_type, expected_cert_name", [(AppDomainCert, "eng-normal-test"), (AppDomainSharedCert, "eng-shared-test")]
    )
    def test_https_cert_created(self, app, cert_type, expected_cert_name):
        cert = G(cert_type, name="test")
        domain_with_cert = DomainWithCert(host="example.com", path_prefix="", https_enabled=True, cert=cert)
        factory = IngressDomainFactory(app)

        domain = factory.create(domain_with_cert)
        assert domain.host == domain_with_cert.host
        assert domain.tls_enabled == domain_with_cert.https_enabled
        assert domain.tls_secret_name == expected_cert_name
