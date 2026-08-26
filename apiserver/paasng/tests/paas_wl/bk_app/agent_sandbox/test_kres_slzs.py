# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""Unit tests for AgentSandboxPodSerializer._construct_pod_spec, focusing on
how VolumeMount items are rendered into ``volumes`` + ``volumeMounts``
(single CSI inline volume + subPath-split mounts). Shared spec construction
is parametrized across Pod and SandboxInstance entities.
"""

import uuid

import pytest
from django.conf import settings

from paas_wl.bk_app.agent_sandbox.constants import (
    DAEMON_COMMAND,
    SANDBOX_INSTANCE_API_VERSION,
    SANDBOX_INSTANCE_NETWORK_MODE,
    SANDBOX_INSTANCE_RUNTIME_CLASS_NAME,
    SHARED_VOLUME_NAME_IN_POD,
)
from paas_wl.bk_app.agent_sandbox.kres_entities import (
    AgentSandboxInstance,
    AgentSandboxKresApp,
    AgentSandboxPod,
    AgentSandboxWorkload,
    VolumeMount,
)
from paas_wl.bk_app.agent_sandbox.kres_slzs import AgentSandboxInstanceSerializer, AgentSandboxPodSerializer
from paas_wl.infras.resources.kube_res.base import GVKConfig
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def sbx_app() -> AgentSandboxKresApp:
    return AgentSandboxKresApp(
        paas_app_id="demo-app",
        tenant_id=DEFAULT_TENANT_ID,
        target=CLUSTER_NAME_FOR_TESTING,
    )


@pytest.fixture(params=[AgentSandboxPod, AgentSandboxInstance], ids=["pod", "sandbox_instance"])
def sandbox_entity_cls(request) -> type[AgentSandboxWorkload]:
    return request.param


def _make_sandbox(sbx_app, entity_cls: type[AgentSandboxWorkload], *, volume_mounts=None, cpu=None, memory=None):
    kwargs = {}
    if cpu is not None:
        kwargs["cpu"] = cpu
    if memory is not None:
        kwargs["memory"] = memory
    return entity_cls.create(
        sbx_app,
        name="test-sandbox",
        sandbox_id="abc123",
        workdir="/workspace",
        snapshot=settings.AGENT_SANDBOX_DEFAULT_IMAGE,
        env={"FOO": "BAR"},
        volume_mounts=volume_mounts,
        **kwargs,
    )


def _vol_id() -> str:
    return str(uuid.uuid4())


class TestConstructPodSpecVolumes:
    """Verify the CSI inline volume + subPath volumeMount layout."""

    def test_no_volume_mounts_omits_volumes(self, sbx_app, sandbox_entity_cls):
        sbx = _make_sandbox(sbx_app, sandbox_entity_cls, volume_mounts=None)
        spec = AgentSandboxPodSerializer._construct_pod_spec(sbx)

        assert "volumes" not in spec
        main_container = spec["containers"][0]
        assert "volumeMounts" not in main_container

    def test_single_volume_mount_is_rw(self, sbx_app, sandbox_entity_cls):
        vid = _vol_id()
        sbx = _make_sandbox(
            sbx_app,
            sandbox_entity_cls,
            volume_mounts=[
                VolumeMount(
                    volume_id=vid,
                    mount_path="/workspace/shared",
                    sub_path=f"app/{vid.replace('-', '')}",
                    read_only=False,
                ),
            ],
        )
        spec = AgentSandboxPodSerializer._construct_pod_spec(sbx)

        assert len(spec["volumes"]) == 1
        vol = spec["volumes"][0]
        assert vol["name"] == SHARED_VOLUME_NAME_IN_POD
        assert vol["csi"]["driver"] == settings.AGENT_SANDBOX_VOLUME_CSI_DRIVER
        assert vol["csi"]["volumeAttributes"] == dict(settings.AGENT_SANDBOX_VOLUME_CSI_ATTRIBUTES)

        mounts = spec["containers"][0]["volumeMounts"]
        assert mounts == [
            {
                "name": SHARED_VOLUME_NAME_IN_POD,
                "mountPath": "/workspace/shared",
                "subPath": f"app/{vid.replace('-', '')}",
                "readOnly": False,
            }
        ]

    def test_two_volumes_share_single_csi_volume(self, sbx_app, sandbox_entity_cls):
        vid1 = _vol_id()
        vid2 = _vol_id()
        sbx = _make_sandbox(
            sbx_app,
            sandbox_entity_cls,
            volume_mounts=[
                VolumeMount(
                    volume_id=vid1,
                    mount_path="/workspace/shared",
                    sub_path=f"app/{vid1.replace('-', '')}",
                    read_only=False,
                ),
                VolumeMount(
                    volume_id=vid2,
                    mount_path="/opt/data",
                    sub_path=f"app/{vid2.replace('-', '')}",
                    read_only=False,
                ),
            ],
        )
        spec = AgentSandboxPodSerializer._construct_pod_spec(sbx)

        # Only a single CSI inline volume is declared regardless of mount count.
        assert len(spec["volumes"]) == 1
        assert spec["volumes"][0]["name"] == SHARED_VOLUME_NAME_IN_POD

        mounts = spec["containers"][0]["volumeMounts"]
        assert len(mounts) == 2
        # All mounts reference the same volume, differentiated by subPath.
        assert all(m["name"] == SHARED_VOLUME_NAME_IN_POD for m in mounts)
        sub_paths = [m["subPath"] for m in mounts]
        assert sub_paths == [f"app/{vid1.replace('-', '')}", f"app/{vid2.replace('-', '')}"]

    def test_csi_attributes_follow_settings(self, sbx_app, sandbox_entity_cls, settings):
        # 验证 driver 与 volumeAttributes 完全由 settings 透传，可适配任意 CSI 实现（如 NFS）
        settings.AGENT_SANDBOX_VOLUME_CSI_DRIVER = "nfs.csi.k8s.io"
        settings.AGENT_SANDBOX_VOLUME_CSI_ATTRIBUTES = {
            "server": "10.0.0.1",
            "share": "/data",
        }

        vid = _vol_id()
        sbx = _make_sandbox(
            sbx_app,
            sandbox_entity_cls,
            volume_mounts=[
                VolumeMount(
                    volume_id=vid,
                    mount_path="/workspace/shared",
                    sub_path=f"app/{vid.replace('-', '')}",
                    read_only=False,
                )
            ],
        )
        spec = AgentSandboxPodSerializer._construct_pod_spec(sbx)
        csi = spec["volumes"][0]["csi"]

        assert csi["driver"] == "nfs.csi.k8s.io"
        assert csi["volumeAttributes"] == {
            "server": "10.0.0.1",
            "share": "/data",
        }


class TestConstructPodSpecResources:
    """Verify resources.limits are derived from the sandbox cpu/memory while
    requests keep the platform default values."""

    def test_default_resources(self, sbx_app, sandbox_entity_cls):
        # 未显式指定时走 AgentSandboxWorkload 的默认值 (2 核 / 1 GB)
        sbx = _make_sandbox(sbx_app, sandbox_entity_cls)
        spec = AgentSandboxPodSerializer._construct_pod_spec(sbx)

        resources = spec["containers"][0]["resources"]
        assert resources["limits"] == {"cpu": "2000m", "memory": "1024Mi"}
        assert resources["requests"] == {"cpu": "50m", "memory": "128Mi"}

    def test_custom_resources(self, sbx_app, sandbox_entity_cls):
        sbx = _make_sandbox(sbx_app, sandbox_entity_cls, cpu=3, memory=2)
        spec = AgentSandboxPodSerializer._construct_pod_spec(sbx)

        resources = spec["containers"][0]["resources"]
        assert resources["limits"] == {"cpu": "3000m", "memory": "2048Mi"}
        # requests 始终保持平台默认值
        assert resources["requests"] == {"cpu": "50m", "memory": "128Mi"}

    def test_limits_not_below_requests(self, sbx_app, sandbox_entity_cls):
        # 即使配置极小的值, limits 也不会低于 requests
        sbx = _make_sandbox(sbx_app, sandbox_entity_cls, cpu=0, memory=0)
        spec = AgentSandboxPodSerializer._construct_pod_spec(sbx)

        resources = spec["containers"][0]["resources"]
        assert resources["limits"] == {"cpu": "50m", "memory": "128Mi"}


class TestAgentSandboxInstanceSerializer:
    """Verify SandboxInstance CR manifest shape (S-002)."""

    def test_serialize_sandbox_instance(self, sbx_app):
        sbx = AgentSandboxInstance.create(
            sbx_app,
            name="si-sandbox",
            sandbox_id="abc123",
            workdir="/workspace",
            snapshot=settings.AGENT_SANDBOX_DEFAULT_IMAGE,
            env={"TOKEN": "t", "SERVER_PORT": "30000"},
            volume_mounts=[
                VolumeMount(
                    volume_id="vol-1",
                    mount_path="/workspace/data",
                    sub_path="app/vol1",
                    read_only=False,
                )
            ],
        )
        gvk_config = GVKConfig(
            server_version="v1.24.0",
            kind="SandboxInstance",
            preferred_apiversion=SANDBOX_INSTANCE_API_VERSION,
            available_apiversions=[SANDBOX_INSTANCE_API_VERSION],
        )
        manifest = AgentSandboxInstanceSerializer(AgentSandboxInstance, gvk_config).serialize(sbx)

        assert manifest["apiVersion"] == SANDBOX_INSTANCE_API_VERSION
        assert manifest["kind"] == "SandboxInstance"
        assert manifest["metadata"]["name"] == "si-sandbox"
        assert manifest["spec"]["desiredState"] == "Running"
        assert manifest["spec"]["runtimeClassName"] == SANDBOX_INSTANCE_RUNTIME_CLASS_NAME
        assert manifest["spec"]["network"]["mode"] == SANDBOX_INSTANCE_NETWORK_MODE
        assert manifest["spec"]["domain"] == {}
        assert manifest["spec"]["podTemplate"]["containers"][0]["name"] == "main"
        assert manifest["spec"]["podTemplate"]["containers"][0]["command"] == DAEMON_COMMAND
        assert manifest["spec"]["podTemplate"]["labels"]["bkapp.paas.bk.tencent.com/sandbox-id"] == "abc123"
        volumes = manifest["spec"]["podTemplate"]["volumes"]
        assert volumes[0]["name"] == SHARED_VOLUME_NAME_IN_POD
        mounts = manifest["spec"]["podTemplate"]["containers"][0]["volumeMounts"]
        assert mounts[0]["mountPath"] == "/workspace/data"
        assert mounts[0]["subPath"] == "app/vol1"
