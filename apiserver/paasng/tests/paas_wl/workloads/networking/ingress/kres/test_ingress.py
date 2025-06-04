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

from textwrap import dedent
from typing import Dict

import pytest
from blue_krill.text import remove_prefix, remove_suffix
from kubernetes.dynamic.resource import ResourceInstance

from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.kube_res.base import GVKConfig
from paas_wl.workloads.networking.ingress.entities import PIngressDomain, PServicePortPair
from paas_wl.workloads.networking.ingress.kres_entities.ingress import ProcessIngress, ingress_kmodel
from paas_wl.workloads.networking.ingress.kres_entities.service import ProcessService, service_kmodel
from paas_wl.workloads.networking.ingress.kres_slzs.ingress import (
    IngressV1Beta1Deserializer,
    IngressV1Beta1Serializer,
    IngressV1Deserializer,
    IngressV1Serializer,
)
from paas_wl.workloads.networking.ingress.kres_slzs.utils import (
    ConfigurationSnippetPatcher,
    NginxRegexRewrittenProvider,
)
from tests.paas_wl.utils.wl_app import create_wl_release

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestProcessIngress:
    @pytest.fixture(autouse=True)
    def _setup_data(self, bk_stag_wl_app, settings):
        settings.ENABLE_MODERN_INGRESS_SUPPORT = True
        create_wl_release(
            wl_app=bk_stag_wl_app,
            release_params={
                "version": 5,
                "procfile": {"web": "python manage.py runserver", "worker": "python manage.py celery"},
            },
        )

    @pytest.fixture()
    def service(self, bk_stag_wl_app):
        service = ProcessService(
            app=bk_stag_wl_app,
            name="foo-service",
            process_type="web",
            ports=[PServicePortPair(name="http", port=80, target_port=80)],
        )

        service_kmodel.save(service)
        return service_kmodel.list_by_app(bk_stag_wl_app)[0]

    @pytest.mark.auto_create_ns
    def test_normal(self, bk_stag_wl_app, service):
        domains = [PIngressDomain(host="foo.com")]
        ingress = ProcessIngress(
            app=bk_stag_wl_app,
            name="normal-service",
            domains=domains,
            service_name=service.name,
            service_port_name=service.ports[0].name,
            rewrite_to_root=True,
            server_snippet="server",
            annotations={"foo": "bar"},
        )
        ingress_kmodel.save(ingress)

        item = ingress_kmodel.get(bk_stag_wl_app, "normal-service")
        assert item is not None
        assert item.server_snippet == "server"
        assert item.annotations == {"foo": "bar"}

    @pytest.mark.auto_create_ns
    def test_paths(self, bk_stag_wl_app, service):
        """Multiple hosts with paths"""
        domains = [
            PIngressDomain(host="foo.com"),
            PIngressDomain(host="bar.com", path_prefix_list=["/foo/", "/extra_bar/"]),
        ]
        ingress = ProcessIngress(
            app=bk_stag_wl_app,
            name="primary-path-service",
            domains=domains,
            service_name=service.name,
            service_port_name=service.ports[0].name,
            rewrite_to_root=True,
        )
        ingress_kmodel.save(ingress)

        item: ProcessIngress = ingress_kmodel.get(bk_stag_wl_app, "primary-path-service")
        assert len(item.domains) == 2
        assert item.domains[0].primary_prefix_path == "/"
        assert item.domains[0].path_prefix_list == ["/"]
        assert item.domains[1].primary_prefix_path == "/foo/"
        assert item.domains[1].path_prefix_list == ["/foo/", "/extra_bar/"]

    def test_serializer_ordering(self, bk_stag_wl_app):
        serializer = ingress_kmodel._make_serializer(bk_stag_wl_app)
        available_apiversions = serializer.gvk_config.available_apiversions

        if "networking.k8s.io/v1beta1" in available_apiversions or "extensions/v1beta1" in available_apiversions:
            assert isinstance(serializer, IngressV1Beta1Serializer)
        elif "networking.k8s.io/v1" in available_apiversions:
            assert isinstance(serializer, IngressV1Serializer)
        else:
            pytest.fail("unknown api version")

    def test_deserializer_ordering(self, bk_stag_wl_app):
        deserializer = ingress_kmodel._make_deserializer(bk_stag_wl_app)
        available_apiversions = deserializer.gvk_config.available_apiversions

        if "networking.k8s.io/v1beta1" in available_apiversions or "extensions/v1beta1" in available_apiversions:
            assert isinstance(deserializer, IngressV1Beta1Deserializer)
        elif "networking.k8s.io/v1" in available_apiversions:
            assert isinstance(deserializer, IngressV1Deserializer)
        else:
            pytest.fail("unknown api versions")


INGRESS_DATA: Dict = {
    "name": "testing",
    "service_name": "test-service",
    "service_port_name": "test-port",
    "configuration_snippet": "configuration_snippet",
    "server_snippet": "server_snippet",
    "annotations": {"FOO": "BAR"},
}


@pytest.fixture()
def root_path():
    return "/"


@pytest.fixture()
def foo_path():
    return "/foo"


@pytest.fixture()
def foo_path_endswith_slash(foo_path):
    return foo_path + "/"


@pytest.fixture()
def https_ingress_domain(root_path, foo_path, foo_path_endswith_slash):
    return PIngressDomain(
        host="https.com",
        tls_enabled=True,
        tls_secret_name="cert",
        path_prefix_list=[root_path, foo_path, foo_path_endswith_slash],
    )


@pytest.fixture()
def http_ingress_domain(root_path, foo_path, foo_path_endswith_slash):
    return PIngressDomain(
        host="http.com", tls_enabled=False, path_prefix_list=[root_path, foo_path, foo_path_endswith_slash]
    )


@pytest.fixture()
def ingress(bk_stag_wl_app, https_ingress_domain, http_ingress_domain):
    return ProcessIngress(
        app=bk_stag_wl_app,
        domains=[https_ingress_domain, http_ingress_domain],
        rewrite_to_root=False,
        **INGRESS_DATA,
    )


@pytest.fixture()
def subpath_ingress(bk_stag_wl_app, https_ingress_domain, http_ingress_domain):
    return ProcessIngress(
        app=bk_stag_wl_app,
        domains=[https_ingress_domain, http_ingress_domain],
        rewrite_to_root=True,
        **INGRESS_DATA,
    )


@pytest.fixture()
def fallback_configuration_snippet(https_ingress_domain):
    return dedent(
        f"""\
            if ($location_path = '') {{
                set $location_path "{https_ingress_domain.primary_prefix_path}";
            }}

            proxy_set_header X-Script-Name $location_path;
            """
    )


@pytest.fixture()
def pattern_configuration_snippet():
    return "proxy_set_header X-Script-Name /$1$3;"


def build_v1beta1_ingress_path(path) -> Dict:
    return {
        "backend": {
            "serviceName": INGRESS_DATA["service_name"],
            "servicePort": INGRESS_DATA["service_port_name"],
        },
        "path": path,
    }


@pytest.mark.parametrize("api_version", ["extensions/v1beta1", "networking.k8s.io/v1beta1"])
class TestIngressV1Beta1:
    @pytest.fixture()
    def spec(
        self, api_version, bk_stag_wl_app, https_ingress_domain, http_ingress_domain, fallback_configuration_snippet
    ):
        return {
            "apiVersion": api_version,
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": ConfigurationSnippetPatcher()
                    .patch(INGRESS_DATA["configuration_snippet"], fallback_configuration_snippet)
                    .configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": INGRESS_DATA["server_snippet"],
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    "bkbcs.tencent.com/skip-filter-clb": "true",
                    **INGRESS_DATA["annotations"],
                },
                "name": INGRESS_DATA["name"],
                "namespace": bk_stag_wl_app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": https_ingress_domain.host,
                        "http": {
                            "paths": [
                                build_v1beta1_ingress_path(path) for path in https_ingress_domain.path_prefix_list
                            ]
                        },
                    },
                    {
                        "host": http_ingress_domain.host,
                        "http": {
                            "paths": [
                                build_v1beta1_ingress_path(path) for path in http_ingress_domain.path_prefix_list
                            ]
                        },
                    },
                ],
                "tls": [{"hosts": [https_ingress_domain.host], "secretName": https_ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def subpath_spec(
        self, api_version, bk_stag_wl_app, https_ingress_domain, http_ingress_domain, fallback_configuration_snippet
    ):
        return {
            "apiVersion": api_version,
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": ConfigurationSnippetPatcher()
                    .patch(INGRESS_DATA["configuration_snippet"], fallback_configuration_snippet)
                    .configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": INGRESS_DATA["server_snippet"],
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "bkbcs.tencent.com/skip-filter-clb": "true",
                    **INGRESS_DATA["annotations"],
                },
                "name": INGRESS_DATA["name"],
                "namespace": bk_stag_wl_app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": https_ingress_domain.host,
                        "http": {
                            "paths": [
                                build_v1beta1_ingress_path(path) for path in https_ingress_domain.path_prefix_list
                            ]
                        },
                    },
                    {
                        "host": http_ingress_domain.host,
                        "http": {
                            "paths": [
                                build_v1beta1_ingress_path(path) for path in http_ingress_domain.path_prefix_list
                            ]
                        },
                    },
                ],
                "tls": [{"hosts": [https_ingress_domain.host], "secretName": https_ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def gvk_config(self, api_version):
        return GVKConfig(
            server_version="0.0.0",
            kind="Ingress",
            preferred_apiversion=api_version,
            available_apiversions=[api_version],
        )

    def test_serialize(self, gvk_config, spec, ingress):
        serializer = IngressV1Beta1Serializer(ProcessIngress, gvk_config)
        result = serializer.serialize(ingress)
        assert result == spec

    def test_serialize_subpath(self, gvk_config, subpath_spec, subpath_ingress):
        serializer = IngressV1Beta1Serializer(ProcessIngress, gvk_config)
        result = serializer.serialize(subpath_ingress)
        assert result == subpath_spec

    @pytest.fixture()
    def kube_data(self, spec):
        return ResourceInstance(None, spec)

    @pytest.fixture()
    def subpath_kube_data(self, subpath_spec):
        return ResourceInstance(None, subpath_spec)

    def test_deserialize(self, gvk_config, bk_stag_wl_app, kube_data, ingress):
        deserializer = IngressV1Beta1Deserializer(ProcessIngress, gvk_config)
        result = deserializer.deserialize(bk_stag_wl_app, kube_data)
        assert result == ingress

    def test_deserialize_subpath(self, gvk_config, bk_stag_wl_app, subpath_kube_data, subpath_ingress):
        deserializer = IngressV1Beta1Deserializer(ProcessIngress, gvk_config)
        result = deserializer.deserialize(bk_stag_wl_app, subpath_kube_data)
        assert result == subpath_ingress


def build_v1_ingress_path(path_str) -> Dict:
    trim_path = remove_prefix(path_str, "/")
    if path_str == "/":
        path = "/()(.*)"
    elif trim_path.endswith("/"):
        path = "/({})/(.*)()".format(remove_suffix(trim_path, "/"))
    else:
        path = "/({})/(.*)|/({}$)".format(trim_path, trim_path)

    return {
        "backend": {
            "service": {
                "name": INGRESS_DATA["service_name"],
                "port": {
                    "name": INGRESS_DATA["service_port_name"],
                },
            }
        },
        "path": path,
        "pathType": "ImplementationSpecific",
    }


class TestProcessIngressV1:
    @pytest.fixture(autouse=True)
    def _setup(self, bk_stag_wl_app, settings):
        # 目前 networking.k8s.io/v1 仅支持正则模式
        cluster = get_cluster_by_app(bk_stag_wl_app)
        cluster.feature_flags[ClusterFeatureFlag.INGRESS_USE_REGEX] = True
        cluster.save()
        settings.ENABLE_MODERN_INGRESS_SUPPORT = True

    @pytest.fixture()
    def subpath_spec(self, bk_stag_wl_app, https_ingress_domain, http_ingress_domain, pattern_configuration_snippet):
        """spec rewrite to root"""
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": ConfigurationSnippetPatcher()
                    .patch(INGRESS_DATA["configuration_snippet"], pattern_configuration_snippet)
                    .configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": INGRESS_DATA["server_snippet"],
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
                    "bkbcs.tencent.com/skip-filter-clb": "true",
                    **INGRESS_DATA["annotations"],
                },
                "name": INGRESS_DATA["name"],
                "namespace": bk_stag_wl_app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": https_ingress_domain.host,
                        "http": {
                            "paths": [build_v1_ingress_path(path) for path in https_ingress_domain.path_prefix_list]
                        },
                    },
                    {
                        "host": http_ingress_domain.host,
                        "http": {
                            "paths": [build_v1_ingress_path(path) for path in http_ingress_domain.path_prefix_list]
                        },
                    },
                ],
                "tls": [{"hosts": [https_ingress_domain.host], "secretName": https_ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="0.0.0",
            kind="Ingress",
            preferred_apiversion="networking.k8s.io/v1",
            available_apiversions=["networking.k8s.io/v1"],
        )

    def test_serialize_subpath(self, gvk_config, subpath_spec, subpath_ingress):
        serializer = IngressV1Serializer(ProcessIngress, gvk_config)
        result = serializer.serialize(subpath_ingress)
        assert result == subpath_spec

    @pytest.fixture()
    def subpath_kube_data(self, subpath_spec):
        return ResourceInstance(None, subpath_spec)

    def test_deserialize_subpath(self, gvk_config, bk_stag_wl_app, subpath_kube_data, subpath_ingress):
        deserializer = IngressV1Deserializer(ProcessIngress, gvk_config)
        result = deserializer.deserialize(bk_stag_wl_app, subpath_kube_data)
        assert result == subpath_ingress


def build_legacy_pattern(path_str):
    if path_str == "/" or not path_str.endswith("/"):
        path = f"{path_str}()(.*)"
    else:
        path = f"{path_str.rstrip('/')}(/|$)(.*)"
    return path


class TestPatternCompatible:
    """测试兼容旧版的正则表达式规则"""

    @pytest.fixture(autouse=True)
    def _setup(self, bk_stag_wl_app, settings):
        # 目前 networking.k8s.io/v1 仅支持正则模式
        cluster = get_cluster_by_app(bk_stag_wl_app)
        cluster.feature_flags[ClusterFeatureFlag.INGRESS_USE_REGEX] = True
        cluster.save()
        settings.ENABLE_MODERN_INGRESS_SUPPORT = True

    @pytest.fixture()
    def v1beta1_spec(self, bk_stag_wl_app, https_ingress_domain, http_ingress_domain):
        return {
            "apiVersion": "networking.k8s.io/v1beta1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": ConfigurationSnippetPatcher()
                    .patch(
                        INGRESS_DATA["configuration_snippet"], NginxRegexRewrittenProvider.make_configuration_snippet()
                    )
                    .configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": INGRESS_DATA["server_snippet"],
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "bkbcs.tencent.com/skip-filter-clb": "true",
                    **INGRESS_DATA["annotations"],
                },
                "name": INGRESS_DATA["name"],
                "namespace": bk_stag_wl_app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": https_ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "serviceName": INGRESS_DATA["service_name"],
                                        "servicePort": INGRESS_DATA["service_port_name"],
                                    },
                                    "path": build_legacy_pattern(path),
                                }
                                for path in https_ingress_domain.path_prefix_list
                            ]
                        },
                    },
                    {
                        "host": http_ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "serviceName": INGRESS_DATA["service_name"],
                                        "servicePort": INGRESS_DATA["service_port_name"],
                                    },
                                    "path": build_legacy_pattern(path),
                                }
                                for path in https_ingress_domain.path_prefix_list
                            ]
                        },
                    },
                ],
                "tls": [{"hosts": [https_ingress_domain.host], "secretName": https_ingress_domain.tls_secret_name}],
            },
        }

    @pytest.fixture()
    def v1_spec(self, bk_stag_wl_app, https_ingress_domain, http_ingress_domain):
        return {
            "apiVersion": "networking.k8s.io/v1beta1",
            "kind": "Ingress",
            "metadata": {
                "annotations": {
                    "nginx.ingress.kubernetes.io/configuration-snippet": ConfigurationSnippetPatcher()
                    .patch(
                        INGRESS_DATA["configuration_snippet"], NginxRegexRewrittenProvider.make_configuration_snippet()
                    )
                    .configuration_snippet,
                    "nginx.ingress.kubernetes.io/server-snippet": INGRESS_DATA["server_snippet"],
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "bkbcs.tencent.com/skip-filter-clb": "true",
                    **INGRESS_DATA["annotations"],
                },
                "name": INGRESS_DATA["name"],
                "namespace": bk_stag_wl_app.namespace,
            },
            "spec": {
                "rules": [
                    {
                        "host": https_ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "service": {
                                            "name": INGRESS_DATA["service_name"],
                                            "port": {"name": INGRESS_DATA["service_port_name"]},
                                        }
                                    },
                                    "pathType": "ImplementationSpecific",
                                    "path": build_legacy_pattern(path),
                                }
                                for path in https_ingress_domain.path_prefix_list
                            ]
                        },
                    },
                    {
                        "host": http_ingress_domain.host,
                        "http": {
                            "paths": [
                                {
                                    "backend": {
                                        "service": {
                                            "name": INGRESS_DATA["service_name"],
                                            "port": {"name": INGRESS_DATA["service_port_name"]},
                                        }
                                    },
                                    "pathType": "ImplementationSpecific",
                                    "path": build_legacy_pattern(path),
                                }
                                for path in https_ingress_domain.path_prefix_list
                            ]
                        },
                    },
                ],
                "tls": [{"hosts": [https_ingress_domain.host], "secretName": https_ingress_domain.tls_secret_name}],
            },
        }

    @pytest.mark.parametrize(
        ("deserializer_cls", "api_version", "spec_fixture"),
        [
            (IngressV1Beta1Deserializer, "networking.k8s.io/v1beta1", "v1beta1_spec"),
            (IngressV1Deserializer, "networking.k8s.io/v1", "v1_spec"),
        ],
    )
    def test_deserialize(self, request, bk_stag_wl_app, deserializer_cls, api_version, spec_fixture, subpath_ingress):
        gvk_config = GVKConfig(
            server_version="0.0.0",
            kind="Ingress",
            preferred_apiversion=api_version,
            available_apiversions=[api_version],
        )
        deserializer = deserializer_cls(ProcessIngress, gvk_config)
        result = deserializer.deserialize(
            bk_stag_wl_app, ResourceInstance(None, request.getfixturevalue(spec_fixture))
        )
        assert result == subpath_ingress
