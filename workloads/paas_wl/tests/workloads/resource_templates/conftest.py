# -*- coding: utf-8 -*-
from textwrap import dedent

import pytest

from paas_wl.workloads.resource_templates.constants import AppAddOnType
from paas_wl.workloads.resource_templates.models import AppAddOnTemplate


@pytest.fixture
def sidecar_template():
    return dedent(
        """
                {
                    "name": "agent",
                    "image": "blueking-fake.com:8090/gitlab-runner/agent:latest",
                    "imagePullPolicy": "Always",
                    "ports": [
                        {
                            "name": "some-config",
                            "containerPort": 7788,
                            "protocol": "UDP"
                        }
                    ]
                }"""
    )


@pytest.fixture
def sidecar_addon_template(sidecar_template):
    return AppAddOnTemplate.objects.create(name='sidecar', spec=sidecar_template, type=AppAddOnType.SIMPLE_SIDECAR)


@pytest.fixture
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


@pytest.fixture
def probe_addon_template(probe_template):
    return AppAddOnTemplate.objects.create(name="probe", spec=probe_template, type=AppAddOnType.READINESS_PROBE)


@pytest.fixture
def shm_volume_mount_template():
    return dedent(
        """
    {
        "mountPath": "/dev/shm",
        "name": "shm"
    }
    """
    )


@pytest.fixture
def shm_volume_mount_addon_template(shm_volume_mount_template):
    return AppAddOnTemplate.objects.create(
        name="shm-mount-point", spec=shm_volume_mount_template, type=AppAddOnType.VOLUME_MOUNT
    )


@pytest.fixture
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


@pytest.fixture
def shm_volume_addon_template(shm_volume_template):
    return AppAddOnTemplate.objects.create(name="shm-momory-mount", spec=shm_volume_template, type=AppAddOnType.VOLUME)


@pytest.fixture
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


@pytest.fixture
def secret_volume_addon_template(secret_volume_template):
    return AppAddOnTemplate.objects.create(
        name="a-secret-volume", spec=secret_volume_template, type=AppAddOnType.VOLUME
    )
