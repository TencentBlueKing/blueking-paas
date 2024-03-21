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
import pytest
from django.conf import settings

from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox, DevSandboxIngress, DevSandboxService, get_service_name
from paas_wl.bk_app.dev_sandbox.kres_slzs import (
    DevSandboxIngressSerializer,
    DevSandboxSerializer,
    DevSandboxServiceSerializer,
    get_dev_sandbox_labels,
)
from paas_wl.infras.resources.kube_res.base import GVKConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestDevSandboxSLZ:
    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="1.20.0",
            kind="Deployment",
            preferred_apiversion="apps/v1",
            available_apiversions=["apps/v1"],
        )

    def test_serialize(self, gvk_config, dev_sandbox_entity):
        slz = DevSandboxSerializer(DevSandbox, gvk_config)
        manifest = slz.serialize(dev_sandbox_entity)

        labels = get_dev_sandbox_labels(dev_sandbox_entity.app)
        assert manifest == {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "labels": labels,
                "name": dev_sandbox_entity.name,
            },
            "spec": {
                "replicas": 1,
                "revisionHistoryLimit": settings.MAX_RS_RETAIN,
                "selector": {"matchLabels": labels},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "containers": [
                            {
                                "name": "dev-sandbox",
                                "image": dev_sandbox_entity.runtime.image,
                                "imagePullPolicy": dev_sandbox_entity.runtime.image_pull_policy,
                                "env": [{"name": "FOO", "value": "test"}],
                                "ports": [
                                    {"containerPort": settings.DEV_SANDBOX_DEVSERVER_PORT},
                                    {"containerPort": settings.CONTAINER_PORT},
                                ],
                                "resources": {
                                    "requests": {"cpu": "200m", "memory": "512Mi"},
                                    "limits": {"cpu": "4", "memory": "2Gi"},
                                },
                            }
                        ],
                    },
                },
            },
        }


class TestDevSandboxServiceSLZ:
    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="1.20.0",
            kind="Service",
            preferred_apiversion="v1",
            available_apiversions=["v1"],
        )

    def test_serialize(self, gvk_config, dev_sandbox_service_entity):
        slz = DevSandboxServiceSerializer(DevSandboxService, gvk_config)
        manifest = slz.serialize(dev_sandbox_service_entity)

        assert manifest == {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": get_service_name(dev_sandbox_service_entity.app),
                "labels": {"env": "dev"},
            },
            "spec": {
                "selector": get_dev_sandbox_labels(dev_sandbox_service_entity.app),
                "ports": [
                    {
                        "name": "devserver",
                        "port": 8000,
                        "targetPort": settings.DEV_SANDBOX_DEVSERVER_PORT,
                        "protocol": "TCP",
                    },
                    {"name": "app", "port": 80, "targetPort": settings.CONTAINER_PORT, "protocol": "TCP"},
                ],
            },
        }


class TestDevSandboxIngressSerializer:
    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="1.20.0",
            kind="Ingress",
            preferred_apiversion="networking.k8s.io/v1",
            available_apiversions=["networking.k8s.io/v1"],
        )

    def test_serialize(self, gvk_config, dev_sandbox_ingress_entity, bk_app, module_name, default_dev_sandbox_cluster):
        slz = DevSandboxIngressSerializer(DevSandboxIngress, gvk_config)
        manifest = slz.serialize(dev_sandbox_ingress_entity)

        service_name = get_service_name(dev_sandbox_ingress_entity.app)
        assert manifest["apiVersion"] == "networking.k8s.io/v1"
        assert manifest["metadata"] == {
            "name": dev_sandbox_ingress_entity.name,
            "annotations": {
                "bkbcs.tencent.com/skip-filter-clb": "true",
                "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
                "nginx.ingress.kubernetes.io/configuration-snippet": "proxy_set_header X-Script-Name /$1$3;",
            },
            "labels": {"env": "dev"},
        }
        assert manifest["spec"]["rules"][0] == {
            "host": f"dev-dot-{module_name}-dot-{bk_app.code}.{default_dev_sandbox_cluster.ingress_config.default_root_domain.name}",
            "http": {
                "paths": [
                    {
                        "path": "/(devserver)/(.*)()",
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {
                                "name": service_name,
                                "port": {"name": "devserver"},
                            },
                        },
                    },
                    {
                        "path": "/()(.*)",
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {
                                "name": service_name,
                                "port": {"name": "app"},
                            },
                        },
                    },
                ]
            },
        }
