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
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Callable, Optional
from unittest import mock

import pytest
import requests
import yaml
from attr import define
from kubernetes.client import models as kmodels
from kubernetes.client.rest import ApiException
from kubernetes.utils.create_from_yaml import create_from_yaml_single_item
from urllib3.util import connection

from paas_wl.infras.resources.base.base import EnhancedApiClient
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.base.kube_client import CoreDynamicClient
from paas_wl.utils.kubestatus import HealthStatusType, check_pod_health_status, parse_pod
from paas_wl.workloads.networking.ingress.kres_entities.ingress import ProcessIngress, ingress_kmodel


@define
class E2EFramework:
    client: EnhancedApiClient
    namespace: str
    pod: kmodels.V1Pod
    reload_checker: Optional[Callable] = None

    @contextmanager
    def ensure_ingress(self, ingress: ProcessIngress):
        """create ingress when enter and delete it when exit"""
        self.create_ingress(ingress)
        yield
        self.delete_ingress(ingress)

    def create_ingress(self, ingress: ProcessIngress) -> ProcessIngress:
        """create ingress and ensure the ingress-nginx-controller have reloaded before return"""
        ingress_kmodel.save(ingress)
        if self.reload_checker:
            self.reload_checker(self, ingress)
        return ingress_kmodel.get(ingress.app, ingress.name)

    def delete_ingress(self, ingress: ProcessIngress):
        """delete ingress and ensure the ingress-nginx-controller have reloaded before return"""
        ingress_kmodel.delete(ingress)
        if self.reload_checker:
            self.reload_checker(self, ingress)


@define
class HttpClient:
    session: requests.Session
    nginx_node_ip: str  # the IP address of the node where ingress-nginx is deployed
    nginx_http_port: int  # the HTTP Port of the nginx exposed on the node\
    nginx_https_port: int  # the HTTPS Port of the nginx exposed on the node

    @contextmanager
    def patch_connection(self):
        """force create connection to (nginx_node_ip, nginx_port) before sending the reqeust"""
        _orig_create_connection = connection.create_connection

        def patched_create_connection(address, *args, **kwargs):
            if address[1] == 443:
                redirect_port = self.nginx_https_port
            else:
                redirect_port = self.nginx_http_port
            return _orig_create_connection((self.nginx_node_ip, redirect_port), *args, **kwargs)

        with mock.patch("urllib3.util.connection.create_connection", new=patched_create_connection):
            yield

    def get(self, url, params=None, **kwargs):
        """Sends a GET request. Returns :class:`Response` object."""
        with self.patch_connection():
            return self.session.get(url, params=params, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        """Sends a POST request. Returns :class:`Response` object."""
        with self.patch_connection():
            return self.session.post(url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        """Sends a PUT request. Returns :class:`Response` object."""
        with self.patch_connection():
            return self.session.put(url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        """Sends a PATCH request. Returns :class:`Response` object."""
        with self.patch_connection():
            return self.session.patch(url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        """Sends a DELETE request. Returns :class:`Response` object."""
        with self.patch_connection():
            self.session.delete(url, **kwargs)


def get_ingress_nginx_pod(namespace: str, client: EnhancedApiClient, try_time: int = 60) -> kmodels.V1Pod:
    """utils to find the ingress controller running pod"""
    for _ in range(try_time):
        results = KPod(client).ops_label.list(
            {"app.kubernetes.io/name": "ingress-nginx", "app.kubernetes.io/component": "controller"},
            namespace=namespace,
        )
        for pod_ in results.items:
            pod = parse_pod(pod_)
            if check_pod_health_status(pod).status == HealthStatusType.HEALTHY:
                return pod
        time.sleep(1)
    pytest.fail("can't find healthy ingress-nginx pod")


class IngressNginxReloadChecker:
    """An implement of nginx reload checker, which will find the keyword `reloaded` in ingress-nginx-controller logs"""

    def __init__(self, retry_time: int = 10):
        self.previous_flags = 0
        self.retry_time = retry_time

    def check_keyword_from_logs(self, framework: E2EFramework, ingress: ProcessIngress):
        for _ in range(self.retry_time):
            logs_resp = KPod(framework.client).get_log(name=framework.pod.metadata.name, namespace=framework.namespace)
            for idx, line in enumerate(logs_resp.readlines()):
                if b"reloaded" in line:
                    if idx > self.previous_flags:
                        # Q: why should check twice?
                        # - should ignore first discovered, because this should be invoked by setup
                        if self.previous_flags == 0:
                            self.previous_flags = idx
                            continue
                        self.previous_flags = idx
                        time.sleep(0.2)
                        return
            time.sleep(1)


def create_from_yaml_allow_conflict(k8s_client: EnhancedApiClient, filepath: Path, namespace: str):
    """Perform an action from a yaml file, ignore resource conflict"""
    with filepath.open() as fh:
        contents = yaml.safe_load_all(fh)
        for data in contents:
            try:
                create_from_yaml_single_item(k8s_client, data, namespace=namespace)
            except ApiException as e:
                # Ignore 409 conflicts error
                if e.status == 409:
                    continue
                raise


def delete_from_yaml_ignore_exception(k8s_client: EnhancedApiClient, filepath: Path, namespace: str):
    """Delete Resource from a yaml file, ignore exception"""
    dynamic_client = CoreDynamicClient(k8s_client)
    with filepath.open() as fh:
        contents = yaml.safe_load_all(fh)
        for data in contents:
            with suppress(Exception):
                api_resource = dynamic_client.get_preferred_resource(data["kind"])
                dynamic_client.delete(api_resource, name=data["metadata"]["name"], namespace=namespace)
