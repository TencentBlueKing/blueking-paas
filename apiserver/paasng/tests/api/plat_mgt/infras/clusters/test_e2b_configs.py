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

import pytest
from django.urls import reverse
from rest_framework import status

from paas_wl.infras.cluster.models import Cluster, ClusterE2BConfig
from paasng.platform.agent_sandbox.e2b.constants import E2BSandboxStatus
from paasng.platform.agent_sandbox.e2b.template_sync.status import is_applied
from paasng.platform.agent_sandbox.models import E2BSandbox
from paasng.platform.applications.models import Application
from tests.paasng.platform.agent_sandbox.e2b.helpers import make_builtin_template, mark_applied
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _url(cluster_name: str) -> str:
    return reverse("plat_mgt.infras.cluster.e2b_config", kwargs={"cluster_name": cluster_name})


@pytest.fixture
def e2b_config(init_default_cluster: Cluster) -> ClusterE2BConfig:
    """给默认租户集群登记一份 e2b 配置"""
    return ClusterE2BConfig.objects.create(
        cluster=init_default_cluster,
        control_plane_url="http://e2b-gateway.bcs-system:8080",
        data_plane_address="e2b.example.com",
        api_key="real-gateway-key",
        tenant_id=init_default_cluster.tenant_id,
    )


def _create_sandbox(app: Application, cluster_name: str, sandbox_status: str) -> E2BSandbox:
    return E2BSandbox.objects.create(
        sandbox_id=f"sbx-{generate_random_string(8)}",
        application=app,
        cluster_name=cluster_name,
        status=sandbox_status,
        tenant_id=app.tenant_id,
    )


class TestRetrieveE2BConfig:
    def test_retrieve(self, plat_mgt_api_client, init_default_cluster, e2b_config):
        resp = plat_mgt_api_client.get(_url(init_default_cluster.name))

        assert resp.status_code == status.HTTP_200_OK
        # api_key 只写不读
        assert resp.json() == {
            "control_plane_url": "http://e2b-gateway.bcs-system:8080",
            "data_plane_address": "e2b.example.com",
            "namespace": "default",
            "enabled": True,
        }

    def test_not_configured(self, plat_mgt_api_client, init_default_cluster):
        resp = plat_mgt_api_client.get(_url(init_default_cluster.name))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cluster_not_exists(self, plat_mgt_api_client):
        resp = plat_mgt_api_client.get(_url("not-exists-cluster"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestUpsertE2BConfig:
    def test_create(self, plat_mgt_api_client, init_default_cluster):
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={
                "control_plane_url": "http://e2b-gateway.bcs-system:8080",
                "data_plane_address": "e2b.example.com",
                "api_key": "real-gateway-key",
            },
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        config = ClusterE2BConfig.objects.get(cluster=init_default_cluster)
        assert config.control_plane_url == "http://e2b-gateway.bcs-system:8080"
        assert config.data_plane_address == "e2b.example.com"
        assert config.api_key == "real-gateway-key"
        assert config.namespace == "default"
        assert config.enabled is True
        assert config.tenant_id == init_default_cluster.tenant_id

    def test_create_with_namespace(self, plat_mgt_api_client, init_default_cluster):
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={
                "control_plane_url": "http://e2b-gateway.bcs-system:8080",
                "data_plane_address": "e2b.example.com",
                "api_key": "real-gateway-key",
                "namespace": "e2b-system",
            },
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert ClusterE2BConfig.objects.get(cluster=init_default_cluster).namespace == "e2b-system"

    @pytest.mark.parametrize("namespace", ["E2B", "-e2b", "e2b_system", "a" * 64])
    def test_create_with_invalid_namespace(self, plat_mgt_api_client, init_default_cluster, namespace):
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={
                "control_plane_url": "http://e2b-gateway.bcs-system:8080",
                "data_plane_address": "e2b.example.com",
                "api_key": "real-gateway-key",
                "namespace": namespace,
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert not ClusterE2BConfig.objects.filter(cluster=init_default_cluster).exists()

    def test_create_without_api_key(self, plat_mgt_api_client, init_default_cluster):
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={"control_plane_url": "http://e2b-gateway:8080", "data_plane_address": "e2b.example.com"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert not ClusterE2BConfig.objects.filter(cluster=init_default_cluster).exists()

    def test_update_keeps_api_key_when_blank(self, plat_mgt_api_client, init_default_cluster, e2b_config):
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={
                "control_plane_url": "https://e2b-gateway.example.com",
                "data_plane_address": "e2b-new.example.com:8443",
                "api_key": "",
                "enabled": False,
            },
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        e2b_config.refresh_from_db()
        assert e2b_config.control_plane_url == "https://e2b-gateway.example.com"
        assert e2b_config.data_plane_address == "e2b-new.example.com:8443"
        assert e2b_config.api_key == "real-gateway-key"
        assert e2b_config.enabled is False

    def test_update_api_key(self, plat_mgt_api_client, init_default_cluster, e2b_config):
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={
                "control_plane_url": e2b_config.control_plane_url,
                "data_plane_address": e2b_config.data_plane_address,
                "api_key": "rotated-gateway-key",
            },
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        e2b_config.refresh_from_db()
        assert e2b_config.api_key == "rotated-gateway-key"

    def test_update_keeps_namespace(self, plat_mgt_api_client, init_default_cluster, e2b_config):
        # 前端提交整张表单时会带上原值
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={
                "control_plane_url": e2b_config.control_plane_url,
                "data_plane_address": e2b_config.data_plane_address,
                "namespace": "default",
            },
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_update_cannot_change_namespace(self, plat_mgt_api_client, init_default_cluster, e2b_config):
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={
                "control_plane_url": e2b_config.control_plane_url,
                "data_plane_address": e2b_config.data_plane_address,
                "api_key": "rotated-gateway-key",
                "namespace": "e2b-system",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

        e2b_config.refresh_from_db()
        assert e2b_config.namespace == "default"
        assert e2b_config.api_key == "real-gateway-key"

    @pytest.mark.parametrize(
        ("control_plane_url", "data_plane_address"),
        [
            ("e2b-gateway:8080", "e2b.example.com"),
            ("ftp://e2b-gateway:8080", "e2b.example.com"),
            ("http://e2b-gateway:8080", "https://e2b.example.com"),
            ("http://e2b-gateway:8080", "e2b.example.com/path"),
            ("http://e2b-gateway:8080", "localhost"),
        ],
    )
    def test_invalid_address(self, plat_mgt_api_client, init_default_cluster, control_plane_url, data_plane_address):
        resp = plat_mgt_api_client.put(
            _url(init_default_cluster.name),
            data={
                "control_plane_url": control_plane_url,
                "data_plane_address": data_plane_address,
                "api_key": "real-gateway-key",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestDestroyE2BConfig:
    def test_destroy(self, plat_mgt_api_client, bk_app, init_default_cluster, e2b_config):
        # 已终止的沙箱不阻止删除
        _create_sandbox(bk_app, init_default_cluster.name, E2BSandboxStatus.TERMINATED.value)

        resp = plat_mgt_api_client.delete(_url(init_default_cluster.name))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not ClusterE2BConfig.objects.filter(cluster=init_default_cluster).exists()

    def test_destroy_forgets_sync_records(self, plat_mgt_api_client, init_default_cluster, e2b_config):
        template = make_builtin_template()
        mark_applied(template, init_default_cluster.name)
        mark_applied(template, "other-cluster")

        resp = plat_mgt_api_client.delete(_url(init_default_cluster.name))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        # 换命名空间重建配置后，模板不能凭旧记录显示为可用
        assert not is_applied(template, init_default_cluster.name)
        assert is_applied(template, "other-cluster")

    @pytest.mark.parametrize("sandbox_status", E2BSandboxStatus.active_values())
    def test_destroy_with_live_sandboxes(
        self, plat_mgt_api_client, bk_app, init_default_cluster, e2b_config, sandbox_status
    ):
        _create_sandbox(bk_app, init_default_cluster.name, sandbox_status)

        resp = plat_mgt_api_client.delete(_url(init_default_cluster.name))

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert ClusterE2BConfig.objects.filter(cluster=init_default_cluster).exists()

    def test_not_configured(self, plat_mgt_api_client, init_default_cluster):
        resp = plat_mgt_api_client.delete(_url(init_default_cluster.name))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
