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
from textwrap import dedent

import pytest

from paas_wl.infras.resource_templates.constants import AppAddOnType
from paas_wl.infras.resource_templates.models import AppAddOnTemplate


@pytest.fixture()
def sidecar_template():
    return dedent(
        """
        {
            "name": "agent",
            "image": "blueking-fake.com:8090/gitlab-runner/agent:latest",
            "imagePullPolicy": "Never",
            "ports": [
                {
                    "name": "some-config",
                    "containerPort": 7788,
                    "protocol": "UDP"
                }
            ]
        }"""
    )


@pytest.fixture()
def sidecar_addon_template(sidecar_template):
    return AppAddOnTemplate.objects.create(name="sidecar", spec=sidecar_template, type=AppAddOnType.SIMPLE_SIDECAR)


@pytest.fixture()
def probe_template():
    return dedent(
        """
        {
            "httpGet": {
                "path": "/healthz",
                "port": 5000
            },
            "initialDelaySeconds": 3,
            "periodSeconds": 3,
            "failureThreshold": 15
        }
        """
    )


@pytest.fixture()
def probe_addon_template(probe_template):
    return AppAddOnTemplate.objects.create(name="probe", spec=probe_template, type=AppAddOnType.READINESS_PROBE)


@pytest.fixture()
def probe_handler_templates():
    return {
        "readiness": {
            "http_get": {"path": "/healthz", "port": 8080},
        },
        "liveness": {"tcp_socket": {"port": "${PORT}"}},
    }


@pytest.fixture()
def port_env():
    return 80


@pytest.fixture()
def shm_volume_mount_template():
    return dedent(
        """
    {
        "mountPath": "/dev/shm",
        "name": "shm"
    }
    """
    )


@pytest.fixture()
def shm_volume_mount_addon_template(shm_volume_mount_template):
    return AppAddOnTemplate.objects.create(
        name="shm-mount-point", spec=shm_volume_mount_template, type=AppAddOnType.VOLUME_MOUNT
    )


@pytest.fixture()
def shm_volume_template():
    return dedent(
        """
        {
            "name": "shm",
            "emptyDir": {
                "medium": "Memory",
                "sizeLimit": "512Mi"
            }
        }
    """
    )


@pytest.fixture()
def shm_volume_addon_template(shm_volume_template):
    return AppAddOnTemplate.objects.create(name="shm-momory-mount", spec=shm_volume_template, type=AppAddOnType.VOLUME)


@pytest.fixture()
def secret_volume_template():
    return dedent(
        """
        {
            "name": "secret",
            "secret": {
                "secretName": "the-secret",
                "items": [
                    {
                        "key": "a",
                        "path": "secret/a",
                        "mode": 420
                    }
                ]
            }
        }
    """
    )


@pytest.fixture()
def process_type():
    return "web"


@pytest.fixture()
def secret_volume_addon_template(secret_volume_template):
    return AppAddOnTemplate.objects.create(
        name="a-secret-volume", spec=secret_volume_template, type=AppAddOnType.VOLUME
    )
