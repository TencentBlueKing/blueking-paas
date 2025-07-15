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
from django.conf import settings

from paas_wl.bk_app.dev_sandbox.conf import DEV_SANDBOX_WORKSPACE
from paas_wl.bk_app.dev_sandbox.constants import DevSandboxEnvKey
from paas_wl.bk_app.dev_sandbox.kres_entities import DevSandbox, DevSandboxIngress, DevSandboxService
from paas_wl.bk_app.dev_sandbox.kres_slzs import (
    DevSandboxIngressSerializer,
    DevSandboxSerializer,
    DevSandboxServiceSerializer,
)
from paas_wl.bk_app.dev_sandbox.labels import get_dev_sandbox_labels
from paas_wl.bk_app.dev_sandbox.names import get_dev_sandbox_service_name
from paas_wl.infras.resources.kube_res.base import GVKConfig

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestDevSandboxSLZ:
    @pytest.fixture()
    def gvk_config(self):
        return GVKConfig(
            server_version="1.20.0",
            kind="Pod",
            preferred_apiversion="v1",
            available_apiversions=["v1"],
        )

    def test_serialize(self, gvk_config, dev_sandbox):
        slz = DevSandboxSerializer(DevSandbox, gvk_config)
        manifest = slz.serialize(dev_sandbox)

        labels = get_dev_sandbox_labels(dev_sandbox.app)
        assert manifest == {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": dev_sandbox.name,
                "labels": labels,
                "annotations": {"bkapp.paas.bk.tencent.com/dev-sandbox-code": dev_sandbox.code},
            },
            "spec": {
                "containers": [
                    {
                        "name": "dev-sandbox",
                        "image": dev_sandbox.runtime.image,
                        "imagePullPolicy": dev_sandbox.runtime.image_pull_policy,
                        "env": [
                            {"name": "FOO", "value": "BAR"},
                            {"name": "WORKSPACE", "value": "/data/workspace"},
                            {"name": "TOKEN", "value": dev_sandbox.runtime.envs[DevSandboxEnvKey.TOKEN]},
                            {"name": "SOURCE_FETCH_METHOD", "value": "BK_REPO"},
                            {"name": "SOURCE_FETCH_URL", "value": "http://bkrepo.example.com"},
                        ],
                        "ports": [
                            {"containerPort": settings.DEV_SANDBOX_DEVSERVER_PORT},
                            {"containerPort": settings.CONTAINER_PORT},
                        ],
                        "readinessProbe": {
                            "httpGet": {"port": settings.DEV_SANDBOX_DEVSERVER_PORT, "path": "/healthz"},
                        },
                        "resources": {
                            "requests": {"cpu": "200m", "memory": "512Mi"},
                            "limits": {"cpu": "4", "memory": "2Gi"},
                        },
                        "volumeMounts": [{"name": "workspace", "mountPath": DEV_SANDBOX_WORKSPACE}],
                    },
                    {
                        "name": "code-editor",
                        "image": settings.DEV_SANDBOX_CODE_EDITOR_IMAGE,
                        "imagePullPolicy": "IfNotPresent",
                        "command": ["/usr/bin/code-server"],
                        "args": ["--bind-addr", "0.0.0.0:8080", "--disable-telemetry", "--disable-update-check"],
                        "env": [
                            {"name": "PASSWORD", "value": dev_sandbox.code_editor_cfg.password},
                            {"name": "DISABLE_TELEMETRY", "value": "true"},
                        ],
                        "ports": [
                            {"containerPort": settings.DEV_SANDBOX_CODE_EDITOR_PORT},
                        ],
                        "readinessProbe": {
                            "httpGet": {"port": settings.DEV_SANDBOX_CODE_EDITOR_PORT, "path": "/healthz"},
                        },
                        "resources": {
                            "requests": {"cpu": "500m", "memory": "1Gi"},
                            "limits": {"cpu": "4", "memory": "2Gi"},
                        },
                        "volumeMounts": [
                            {"name": "workspace", "mountPath": DEV_SANDBOX_WORKSPACE},
                            {
                                "name": "code-editor-config",
                                "mountPath": "/home/coder/.local/share/code-server/User/settings.json",
                                "subPath": "settings.json",
                            },
                        ],
                    },
                ],
                "volumes": [
                    {
                        "name": "workspace",
                        "emptyDir": {"sizeLimit": "1Gi"},
                    },
                    {
                        "name": "code-editor-config",
                        "configMap": {
                            "name": f"{dev_sandbox.name}-code-editor-config",
                        },
                    },
                ],
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

    def test_serialize(self, gvk_config, dev_sandbox_service):
        slz = DevSandboxServiceSerializer(DevSandboxService, gvk_config)
        manifest = slz.serialize(dev_sandbox_service)

        assert manifest == {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": get_dev_sandbox_service_name(dev_sandbox_service.app),
                "labels": {"env": "dev"},
            },
            "spec": {
                "selector": get_dev_sandbox_labels(dev_sandbox_service.app),
                "ports": [
                    {
                        "name": "devserver",
                        "port": 8000,
                        "targetPort": settings.DEV_SANDBOX_DEVSERVER_PORT,
                        "protocol": "TCP",
                    },
                    {
                        "name": "app",
                        "port": 80,
                        "targetPort": settings.CONTAINER_PORT,
                        "protocol": "TCP",
                    },
                    {
                        "name": "code-editor",
                        "port": 10251,
                        "targetPort": settings.DEV_SANDBOX_CODE_EDITOR_PORT,
                        "protocol": "TCP",
                    },
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

    def test_serialize(self, gvk_config, dev_sandbox_model, dev_sandbox_ingress, default_cluster):
        slz = DevSandboxIngressSerializer(DevSandboxIngress, gvk_config)
        manifest = slz.serialize(dev_sandbox_ingress)

        svc_name = get_dev_sandbox_service_name(dev_sandbox_ingress.app)
        assert manifest["apiVersion"] == "networking.k8s.io/v1"
        assert manifest["metadata"] == {
            "name": dev_sandbox_ingress.name,
            "annotations": {
                "bkbcs.tencent.com/skip-filter-clb": "true",
                "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
                "nginx.ingress.kubernetes.io/configuration-snippet": "proxy_set_header X-Script-Name /$1$3;",
            },
            "labels": {"env": "dev"},
        }
        assert manifest["spec"]["rules"][0] == {
            "host": f"dev-dot-{dev_sandbox_model.module.name}-dot-{dev_sandbox_model.module.application.code}."
            + default_cluster.ingress_config.default_root_domain.name,
            "http": {
                "paths": [
                    {
                        "path": f"/(dev_sandbox/{dev_sandbox_model.code}/devserver)/(.*)()",
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {
                                "name": svc_name,
                                "port": {"name": "devserver"},
                            },
                        },
                    },
                    {
                        "path": f"/(dev_sandbox/{dev_sandbox_model.code}/app)/(.*)()",
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {
                                "name": svc_name,
                                "port": {"name": "app"},
                            },
                        },
                    },
                    {
                        "path": f"/(dev_sandbox/{dev_sandbox_model.code}/code_editor)/(.*)()",
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {
                                "name": svc_name,
                                "port": {"name": "code-editor"},
                            },
                        },
                    },
                ]
            },
        }
