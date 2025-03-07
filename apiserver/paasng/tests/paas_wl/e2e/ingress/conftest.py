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

import time

import pytest
import requests
from django.conf import settings
from django_dynamic_fixture import G

from paas_wl.bk_app.applications.models import Config, WlApp
from paas_wl.core.resource import get_process_selector
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.workloads.networking.ingress.entities import PIngressDomain, PServicePortPair
from paas_wl.workloads.networking.ingress.kres_entities.ingress import ProcessIngress
from paas_wl.workloads.networking.ingress.kres_entities.service import ProcessService, service_kmodel
from tests.paas_wl.e2e.ingress.utils import E2EFramework, HttpClient, get_ingress_nginx_pod
from tests.paas_wl.utils.basic import random_resource_name
from tests.paas_wl.utils.wl_app import create_wl_release


@pytest.fixture(scope="session")
def ingress_nginx_ns():
    return "ingress-nginx"


@pytest.fixture(scope="session")
def cluster(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return Cluster.objects.get(is_default=True, region=settings.DEFAULT_REGION_NAME)


@pytest.fixture(scope="session")
def k8s_client(cluster):
    return get_client_by_cluster_name(cluster.name)


@pytest.fixture(scope="module")
def ingress_nginx_reload_checker():
    def sleep_only(framework: E2EFramework, ingress: ProcessIngress):
        time.sleep(5)

    return sleep_only


@pytest.fixture(scope="module")
def framework(
    _setup_ingress_nginx_controller, ingress_nginx_ns, ingress_nginx_reload_checker, k8s_client
) -> E2EFramework:
    pod = get_ingress_nginx_pod(namespace=ingress_nginx_ns, client=k8s_client)
    return E2EFramework(
        client=k8s_client,
        namespace=ingress_nginx_ns,
        pod=pod,
        reload_checker=ingress_nginx_reload_checker,
    )


@pytest.fixture(scope="session", autouse=True)
def _skip_if_configuration_not_ready(request):
    if not settings.FOR_TEST_E2E_INGRESS_CONFIG:
        pytest.skip("nginx-ingress e2e configuration not ready, skip e2e test")

    if not request.config.getvalue("run_e2e_test"):
        pytest.skip("run_e2e_test is disabled, skip e2e test")


@pytest.fixture(scope="session")
def http_client():
    return HttpClient(
        session=requests.session(),
        nginx_node_ip=settings.FOR_TEST_E2E_INGRESS_CONFIG["NGINX_NODE_IP"],
        nginx_http_port=settings.FOR_TEST_E2E_INGRESS_CONFIG["NGINX_HTTP_PORT"],
        nginx_https_port=settings.FOR_TEST_E2E_INGRESS_CONFIG["NGINX_HTTPS_PORT"],
    )


# fixture for buildup Ingress and testcase
@pytest.fixture(scope="module")
def echo_hostname():
    return "echo.com"


@pytest.fixture(scope="module")
def root_path():
    return "/"


@pytest.fixture(scope="module")
def foo_path():
    return "/foo"


@pytest.fixture(scope="module")
def multi_layer_path_endswith_slash():
    return "/multi/layer/"


@pytest.fixture(scope="module")
def http_ingress_domain(echo_hostname, root_path, foo_path, multi_layer_path_endswith_slash):
    return PIngressDomain(
        host=echo_hostname, tls_enabled=False, path_prefix_list=[root_path, foo_path, multi_layer_path_endswith_slash]
    )


@pytest.fixture(scope="module")
def e2e_app(namespace_maker, django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        app = G(WlApp, region=settings.DEFAULT_REGION_NAME, structure={"web": 1}, name=random_resource_name())
        G(
            Config,
            app=app,
            metadata={
                "environment": "prod",
                "paas_app_code": "paas-" + app.name,
                "module_name": "default",
            },
        )
        create_wl_release(app)
        namespace_maker.make(app.namespace)
        namespace_maker.set_block()
        yield app
        app.delete()


# Note: ingress_kmodel.save 会修改 ProcessIngress, 因此需要设置 scope=function
@pytest.fixture(scope="function")
def echo_ingress(e2e_app, http_ingress_domain, echo_service):
    """Ingress for EchoService"""
    return ProcessIngress(
        app=e2e_app,
        name="echo-ingress",
        domains=[http_ingress_domain],
        rewrite_to_root=True,
        service_name=echo_service.name,
        service_port_name=echo_service.ports[0].name,
        annotations={"kubernetes.io/ingress.class": "nginx"},
    )


@pytest.fixture(scope="module")
def echo_pod(namespace_maker, framework, e2e_app):
    """An echo server is a server that replicates the request sent by the client and sends it back."""
    kube_selector = get_process_selector(e2e_app, "web")
    pod_dict = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": e2e_app.scheduler_safe_name, "labels": kube_selector},
        "spec": {
            "containers": [
                {
                    "name": "main",
                    "imagePullPolicy": "IfNotPresent",
                    # An echo server is a server that replicates the request sent by the client and sends it back.
                    # ref: https://hub.docker.com/r/ealen/echo-server
                    "image": "ealen/echo-server:0.7.0",
                    "env": [{"name": "PORT", "value": str(settings.CONTAINER_PORT)}],
                    "ports": [{"containerPort": settings.CONTAINER_PORT}],
                }
            ],
            "restartPolicy": "Always",
        },
    }
    pod = KPod(framework.client).create_or_update(
        e2e_app.scheduler_safe_name,
        namespace=e2e_app.namespace,
        body=pod_dict,
    )
    KPod(framework.client).wait_for_status(
        e2e_app.scheduler_safe_name, target_statuses=["Running"], namespace=e2e_app.namespace, timeout=60
    )
    return pod


@pytest.fixture(scope="module")
def echo_service(framework, e2e_app) -> ProcessService:
    """Service for EchoPod"""
    svc = ProcessService(
        app=e2e_app,
        name="echo-service",
        process_type="web",
        ports=[PServicePortPair(name="http", port=80, target_port=settings.CONTAINER_PORT)],
    )
    service_kmodel.save(svc)
    return service_kmodel.get(e2e_app, name=svc.name)
