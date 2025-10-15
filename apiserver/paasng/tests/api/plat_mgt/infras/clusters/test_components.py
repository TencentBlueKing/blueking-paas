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

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status

from paasng.plat_mgt.infras.clusters.constants import CLUSTER_COMPONENT_DEFAULT_QUOTA
from tests.utils.mocks.bcs import StubBCSUserClient
from tests.utils.mocks.helm import StubHelmClient

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(autouse=True)
def _patch_helm_client():
    with patch("paasng.plat_mgt.infras.clusters.views.components.HelmClient", new=StubHelmClient):
        yield


class TestListClusterComponents:
    def test_list(self, plat_mgt_api_client, init_system_cluster):
        resp = plat_mgt_api_client.get(
            reverse("plat_mgt.infras.cluster.component.list", kwargs={"cluster_name": init_system_cluster.name})
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == [
            {
                "name": "bk-ingress-nginx",
                "required": True,
                "status": "installed",
            },
            {
                "name": "bk-log-collector",
                "required": True,
                "status": "installation_failed",
            },
            {
                "name": "bkapp-log-collection",
                "required": True,
                "status": "installation_failed",
            },
            {
                "name": "bkpaas-app-operator",
                "required": True,
                "status": "installing",
            },
            {
                "name": "bcs-general-pod-autoscaler",
                "required": False,
                "status": "not_installed",
            },
        ]


class TestRetrieveClusterComponent:
    def test_retrieve_deployed_component(self, plat_mgt_api_client, init_system_cluster):
        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.component.upsert_retrieve",
                kwargs={"cluster_name": init_system_cluster.name, "component_name": "bk-ingress-nginx"},
            )
        )
        assert resp.status_code == status.HTTP_200_OK

        resp_data = resp.json()
        assert resp_data["chart"]["name"] == "bk-ingress-nginx"
        assert resp_data["release"]["name"] == "bk-ingress-nginx"
        assert resp_data["release"]["namespace"] == "blueking"
        assert resp_data["release"]["status"] == "deployed"
        assert resp_data["values"] == {
            "image": {"registry": "hub.bktencent.com"},
            "hostNetwork": False,
            "replicaCount": 1,
            "service": {"nodePorts": {"http": 30180, "https": 30543}},
            "nodeSelector": {},
            "resources": CLUSTER_COMPONENT_DEFAULT_QUOTA,
        }

    def test_retrieve_install_failed_component(self, plat_mgt_api_client, init_system_cluster):
        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.component.upsert_retrieve",
                kwargs={"cluster_name": init_system_cluster.name, "component_name": "bkapp-log-collection"},
            )
        )
        assert resp.status_code == status.HTTP_200_OK

        resp_data = resp.json()
        assert resp_data["release"]["name"] == "bkapp-log-collection"
        assert resp_data["release"]["status"] == "failed"
        assert resp_data["values"] == {
            "global": {
                "elasticSearchUsername": "blueking",
                "elasticSearchPassword": "blueking",
                "elasticSearchScheme": "https",
                "elasticSearchHost": "127.0.0.12",
                "elasticSearchPort": 9200,
            },
            "bkapp-filebeat": {
                "image": {"registry": "hub.bktencent.com"},
                "containersLogPath": "/var/lib/docker/containers",
            },
            "bkapp-logstash": {
                "image": {"registry": "hub.bktencent.com"},
                "appLogPrefix": "bk_paas3_app",
                "ingressLogPrefix": "bk_paas3_ingress",
            },
        }

    def test_retrieve_not_installed(self, plat_mgt_api_client, init_system_cluster):
        resp = plat_mgt_api_client.get(
            reverse(
                "plat_mgt.infras.cluster.component.upsert_retrieve",
                kwargs={"cluster_name": init_system_cluster.name, "component_name": "bcs-general-pod-autoscaler"},
            )
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestUpsertClusterComponent:
    @pytest.fixture(autouse=True)
    def _patch_bcs_user_client(self):
        with (
            patch("paasng.plat_mgt.infras.clusters.views.components.BCSUserClient", new=StubBCSUserClient),
            patch("paasng.plat_mgt.infras.clusters.views.components.ensure_k8s_namespace", return_value=None),
            patch(
                "paasng.plat_mgt.infras.clusters.views.components."
                "ClusterComponentViewSet._get_component_cur_and_latest_version",
                return_value=("1.0.1", "1.5.4"),
            ),
        ):
            yield

    def test_upsert_bk_ingress_nginx(self, plat_mgt_api_client, init_default_cluster):
        with patch("paasng.plat_mgt.infras.clusters.views.components.BCSUserClient") as mock_bcs_client:
            inst = mock_bcs_client.return_value
            inst.upgrade_release = MagicMock()

            resp = plat_mgt_api_client.post(
                reverse(
                    "plat_mgt.infras.cluster.component.upsert_retrieve",
                    kwargs={"cluster_name": init_default_cluster.name, "component_name": "bk-ingress-nginx"},
                ),
                data={
                    "values": {
                        "hostNetwork": False,
                        "replicaCount": 3,
                        "service": {"nodePorts": {"http": 31180, "https": 31543}},
                        "nodeSelector": {
                            "kubernetes.io/os": "linux",
                        },
                    }
                },
            )
            assert resp.status_code == status.HTTP_204_NO_CONTENT

            assert inst.upgrade_release.called
            called_args = inst.upgrade_release.call_args[0]
            sent_values = called_args[-1]
            assert sent_values["replicaCount"] == 3

    def test_upsert_bkapp_log_collection(self, plat_mgt_api_client, init_default_cluster):
        resp = plat_mgt_api_client.post(
            reverse(
                "plat_mgt.infras.cluster.component.upsert_retrieve",
                kwargs={"cluster_name": init_default_cluster.name, "component_name": "bkapp-log-collection"},
            ),
            data={"values": {}},
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
