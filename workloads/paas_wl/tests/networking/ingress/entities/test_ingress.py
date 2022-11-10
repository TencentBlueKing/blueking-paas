# -*- coding: utf-8 -*-
import pytest
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.networking.ingress.constants import DomainsStructureType
from paas_wl.networking.ingress.entities.ingress import (
    PIngressDomain,
    ProcessIngress,
    ProcessIngressDeserializerExtV1beta1,
    ProcessIngressDeserializerV1,
    ProcessIngressDeserializerV1beta1,
    ProcessIngressSerializerExtV1beta1,
    ProcessIngressSerializerV1,
    ProcessIngressSerializerV1beta1,
    build_ingress_configs,
    ingress_kmodel,
)
from paas_wl.networking.ingress.entities.service import ProcessService, PServicePortPair, service_kmodel
from paas_wl.networking.ingress.models import get_default_subpath
from paas_wl.resources.kube_res.base import GVKConfig
from tests.utils.app import release_setup

pytestmark = pytest.mark.django_db


class TestProcessIngressStructType:
    def test_all_direct_access(self, ingress):
        ingress.domains = [
            PIngressDomain(host='foo.example.com', path_prefix_list=['/']),
            PIngressDomain(host='bar.example.com', path_prefix_list=['/']),
        ]
        assert ingress.domains_structure_type == DomainsStructureType.ALL_DIRECT_ACCESS

    def test_customized_subpath_single(self, ingress):
        ingress.domains = [
            PIngressDomain(host='foo.example.com', path_prefix_list=['/foo/', '/foobar/']),
        ]
        assert ingress.domains_structure_type == DomainsStructureType.CUSTOMIZED_SUBPATH

    def test_customized_subpath_many_valid(self, ingress):
        ingress.domains = [
            PIngressDomain(host='foo.example.com', path_prefix_list=['/foo/', '/foobar/']),
            PIngressDomain(host='bar.example.com', path_prefix_list=['/foo/', '/foobar/']),
        ]
        assert ingress.domains_structure_type == DomainsStructureType.CUSTOMIZED_SUBPATH

    def test_customized_subpath_many_invalid(self, ingress):
        ingress.domains = [
            PIngressDomain(host='foo.example.com', path_prefix_list=['/foo/', '/foobar/']),
            # Another domain has different path_prefixes
            PIngressDomain(host='bar.example.com', path_prefix_list=['/bar/', '/barbar/']),
        ]
        assert ingress.domains_structure_type == DomainsStructureType.NON_STANDARD

    def test_non_standard_mixed_path(self, ingress):
        ingress.domains = [
            PIngressDomain(host='foo.example.com', path_prefix_list=['/bar/', '/foobar/']),
            PIngressDomain(host='bar.example.com', path_prefix_list=['/', '/foobar/']),
        ]
        assert ingress.domains_structure_type == DomainsStructureType.NON_STANDARD

    def test_non_standard_path_invalid(self, ingress):
        ingress.domains = [
            PIngressDomain(host='foo.example.com', path_prefix_list=['/', '/foobar/']),
        ]
        assert ingress.domains_structure_type == DomainsStructureType.NON_STANDARD


class TestProcessIngress:
    @pytest.fixture(autouse=True)
    def _setup_data(self, app, settings):
        settings.ENABLE_MODERN_INGRESS_SUPPORT = True
        ProcessIngress.Meta.deserializers, ProcessIngress.Meta.serializers = build_ingress_configs()
        release_setup(
            fake_app=app,
            build_params={"procfile": {"web": "python manage.py runserver", "worker": "python manage.py celery"}},
            release_params={"version": 5},
        )

    @pytest.fixture()
    def service(self, app):
        service = ProcessService(
            app=app,
            name='foo-service',
            process_type='web',
            ports=[PServicePortPair(name='http', port=80, target_port=80)],
        )

        service_kmodel.save(service)
        return service_kmodel.list_by_app(app)[0]

    @pytest.mark.auto_create_ns
    def test_normal(self, app, service):
        domains = [PIngressDomain(host='foo.com')]
        ingress = ProcessIngress(
            app=app,
            name='normal-service',
            domains=domains,
            service_name=service.name,
            service_port_name=service.ports[0].name,
            server_snippet='server',
            annotations={'foo': 'bar'},
        )
        ingress_kmodel.save(ingress)

        item = ingress_kmodel.get(app, 'normal-service')
        assert item is not None
        assert item.server_snippet == 'server'
        assert item.annotations == {'foo': 'bar'}

    @pytest.mark.auto_create_ns
    def test_paths(self, app, service):
        """Multiple hosts with paths"""
        domains = [
            PIngressDomain(host='foo.com'),
            PIngressDomain(host='bar.com', path_prefix_list=['/foo/', '/extra_bar/']),
        ]
        ingress = ProcessIngress(
            app=app,
            name='primary-path-service',
            domains=domains,
            service_name=service.name,
            service_port_name=service.ports[0].name,
        )
        ingress_kmodel.save(ingress)

        item: ProcessIngress = ingress_kmodel.get(app, 'primary-path-service')
        assert len(item.domains) == 2
        assert item.domains[0].primary_prefix_path == '/'
        assert item.domains[0].path_prefix_list == ['/']
        assert item.domains[1].primary_prefix_path == '/foo/'
        assert item.domains[1].path_prefix_list == ['/foo/', '/extra_bar/']

    def test_serializer_ordering(self, app):
        serializer = ingress_kmodel._make_serializer(app)
        available_apiversions = serializer.gvk_config.available_apiversions

        if ProcessIngressSerializerV1.api_version in available_apiversions:
            assert isinstance(serializer, ProcessIngressSerializerV1)
        elif ProcessIngressSerializerV1beta1.api_version in available_apiversions:
            assert isinstance(serializer, ProcessIngressSerializerV1beta1)
        elif ProcessIngressSerializerExtV1beta1.api_version in available_apiversions:
            assert isinstance(serializer, ProcessIngressSerializerExtV1beta1)
        else:
            pytest.fail("unknown serializer")

    def test_deserializer_ordering(self, app):
        deserializer = ingress_kmodel._make_deserializer(app)
        available_apiversions = deserializer.gvk_config.available_apiversions

        if ProcessIngressDeserializerV1.api_version in available_apiversions:
            assert isinstance(deserializer, ProcessIngressDeserializerV1)
        elif ProcessIngressDeserializerV1beta1.api_version in available_apiversions:
            assert isinstance(deserializer, ProcessIngressDeserializerV1beta1)
        elif ProcessIngressDeserializerExtV1beta1.api_version in available_apiversions:
            assert isinstance(deserializer, ProcessIngressDeserializerExtV1beta1)
        else:
            pytest.fail("unknown deserializer")


def test_get_sub_path(app):
    assert isinstance(get_default_subpath(app), str)


@pytest.fixture()
def ingress_domain():
    return PIngressDomain(host="foo.com", tls_enabled=True, tls_secret_name="cert", path_prefix_list=["/app/"])


@pytest.fixture()
def ingress(app, ingress_domain):
    return ProcessIngress(
        app=app,
        name="testing",
        domains=[ingress_domain],
        service_name="test-service",
        service_port_name="test-port",
        server_snippet="server",
        configuration_snippet="location",
        annotations={"foo": "bar"},
        rewrite_to_root=False,
    )


@pytest.fixture()
def subpath_ingress(app, ingress_domain):
    return ProcessIngress(
        app=app,
        name="testing",
        domains=[ingress_domain],
        service_name="test-service",
        service_port_name="test-port",
        server_snippet="server",
        configuration_snippet="location",
        annotations={"foo": "bar"},
        rewrite_to_root=True,
    )


class TestProcessIngressX1:
    @pytest.fixture()
    def spec(self, app, ingress_domain, ingress):
        return {
            "apiVersion": "extensions/v1beta1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": ingress.configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": ingress.server_snippet,
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    **ingress.annotations,
                },
                "name": ingress.name,
                "namespace": app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "serviceName": ingress.service_name,
                                        "servicePort": ingress.service_port_name,
                                    },
                                    "path": ingress_domain.path_prefix_list[0],
                                }
                            ]
                        },
                    }
                ],
                "tls": [{"hosts": [ingress_domain.host], "secretName": ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def subpath_spec(self, app, ingress_domain, subpath_ingress):
        return {
            "apiVersion": "extensions/v1beta1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": subpath_ingress.configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": subpath_ingress.server_snippet,
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    **subpath_ingress.annotations,
                },
                "name": subpath_ingress.name,
                "namespace": app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "serviceName": subpath_ingress.service_name,
                                        "servicePort": subpath_ingress.service_port_name,
                                    },
                                    "path": ingress_domain.path_prefix_list[0],
                                }
                            ]
                        },
                    }
                ],
                "tls": [{"hosts": [ingress_domain.host], "secretName": ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="0.0.0",
            kind='Ingress',
            preferred_apiversion="extensions/v1beta1",
            available_apiversions=["extensions/v1beta1"],
        )

    def test_serialize(self, gvk_config, spec, ingress):
        serializer = ProcessIngressSerializerExtV1beta1(ProcessIngress, gvk_config)
        result = serializer.serialize(ingress)
        assert result == spec

    def test_serialize_subpath(self, gvk_config, subpath_spec, subpath_ingress):
        serializer = ProcessIngressSerializerExtV1beta1(ProcessIngress, gvk_config)
        result = serializer.serialize(subpath_ingress)
        assert result == subpath_spec

    @pytest.fixture()
    def kube_data(self, spec):
        return ResourceInstance(None, spec)

    @pytest.fixture()
    def subpath_kube_data(self, subpath_spec):
        return ResourceInstance(None, subpath_spec)

    def test_deserialize(self, gvk_config, app, kube_data, ingress):
        deserializer = ProcessIngressDeserializerExtV1beta1(ProcessIngress, gvk_config)
        result = deserializer.deserialize(app, kube_data)
        assert result == ingress

    def test_deserialize_subpath(self, gvk_config, app, subpath_kube_data, subpath_ingress):
        deserializer = ProcessIngressDeserializerExtV1beta1(ProcessIngress, gvk_config)
        result = deserializer.deserialize(app, subpath_kube_data)
        assert result == subpath_ingress


class TestProcessIngressV1:
    @pytest.fixture()
    def spec(self, app, ingress_domain, ingress):
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": ingress.configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": ingress.server_snippet,
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    **ingress.annotations,
                },
                "name": ingress.name,
                "namespace": app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "service": {
                                            "name": ingress.service_name,
                                            "port": {
                                                "name": ingress.service_port_name,
                                            },
                                        }
                                    },
                                    "path": ingress_domain.path_prefix_list[0],
                                    "pathType": "ImplementationSpecific",
                                }
                            ]
                        },
                    }
                ],
                "tls": [{"hosts": [ingress_domain.host], "secretName": ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def subpath_spec(self, app, ingress_domain, subpath_ingress):
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": subpath_ingress.configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": subpath_ingress.server_snippet,
                    "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    **subpath_ingress.annotations,
                },
                "name": subpath_ingress.name,
                "namespace": app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "service": {
                                            "name": subpath_ingress.service_name,
                                            "port": {
                                                "name": subpath_ingress.service_port_name,
                                            },
                                        }
                                    },
                                    "path": f"{ingress_domain.path_prefix_list[0].rstrip('/')}(/|$)(.*)",
                                    "pathType": "ImplementationSpecific",
                                }
                            ]
                        },
                    }
                ],
                "tls": [{"hosts": [ingress_domain.host], "secretName": ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="0.0.0",
            kind='Ingress',
            preferred_apiversion="networking.k8s.io/v1",
            available_apiversions=["networking.k8s.io/v1"],
        )

    def test_serialize(self, gvk_config, spec, ingress):
        serializer = ProcessIngressSerializerV1(ProcessIngress, gvk_config)
        result = serializer.serialize(ingress)
        assert result == spec

    def test_serialize_subpath(self, gvk_config, subpath_spec, subpath_ingress):
        serializer = ProcessIngressSerializerV1(ProcessIngress, gvk_config)
        result = serializer.serialize(subpath_ingress)
        assert result == subpath_spec

    @pytest.fixture()
    def kube_data(self, spec):
        return ResourceInstance(None, spec)

    @pytest.fixture()
    def subpath_kube_data(self, subpath_spec):
        return ResourceInstance(None, subpath_spec)

    def test_deserialize(self, gvk_config, app, kube_data, ingress):
        deserializer = ProcessIngressDeserializerV1(ProcessIngress, gvk_config)
        result = deserializer.deserialize(app, kube_data)
        assert result == ingress

    def test_deserialize_subpath(self, gvk_config, app, subpath_kube_data, subpath_ingress):
        deserializer = ProcessIngressDeserializerV1(ProcessIngress, gvk_config)
        result = deserializer.deserialize(app, subpath_kube_data)
        assert result == subpath_ingress


class TestProcessIngressV1beta1:
    @pytest.fixture()
    def spec(self, app, ingress_domain, ingress):
        return {
            "apiVersion": "networking.k8s.io/v1beta1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": ingress.configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": ingress.server_snippet,
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    **ingress.annotations,
                },
                "name": ingress.name,
                "namespace": app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "serviceName": ingress.service_name,
                                        "servicePort": ingress.service_port_name,
                                    },
                                    "path": ingress_domain.path_prefix_list[0],
                                }
                            ]
                        },
                    }
                ],
                "tls": [{"hosts": [ingress_domain.host], "secretName": ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def subpath_spec(self, app, ingress_domain, subpath_ingress):
        return {
            "apiVersion": "networking.k8s.io/v1beta1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": subpath_ingress.configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": subpath_ingress.server_snippet,
                    "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    **subpath_ingress.annotations,
                },
                "name": subpath_ingress.name,
                "namespace": app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "serviceName": subpath_ingress.service_name,
                                        "servicePort": subpath_ingress.service_port_name,
                                    },
                                    "path": f"{ingress_domain.path_prefix_list[0].rstrip('/')}(/|$)(.*)",
                                }
                            ]
                        },
                    }
                ],
                "tls": [{"hosts": [ingress_domain.host], "secretName": ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="0.0.0",
            kind='Ingress',
            preferred_apiversion="networking.k8s.io/v1beta1",
            available_apiversions=["networking.k8s.io/v1beta1"],
        )

    def test_serialize(self, gvk_config, spec, ingress):
        serializer = ProcessIngressSerializerV1beta1(ProcessIngress, gvk_config)
        result = serializer.serialize(ingress)
        assert result == spec

    def test_serialize_subpath(self, gvk_config, subpath_spec, subpath_ingress):
        serializer = ProcessIngressSerializerV1beta1(ProcessIngress, gvk_config)
        result = serializer.serialize(subpath_ingress)
        assert result == subpath_spec

    @pytest.fixture()
    def kube_data(self, spec):
        return ResourceInstance(None, spec)

    @pytest.fixture()
    def subpath_kube_data(self, subpath_spec):
        return ResourceInstance(None, subpath_spec)

    def test_deserialize(self, gvk_config, app, kube_data, ingress):
        deserializer = ProcessIngressDeserializerV1beta1(ProcessIngress, gvk_config)
        result = deserializer.deserialize(app, kube_data)
        assert result == ingress

    def test_deserialize_subpath(self, gvk_config, app, subpath_kube_data, subpath_ingress):
        deserializer = ProcessIngressDeserializerV1beta1(ProcessIngress, gvk_config)
        result = deserializer.deserialize(app, subpath_kube_data)
        assert result == subpath_ingress
