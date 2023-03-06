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
"""TestDoubles for paasng.engine module"""
from contextlib import contextmanager
from typing import Dict, Optional
from unittest import mock

import cattr
from django.conf import settings

from paas_wl.cluster.constants import ClusterFeatureFlag, ClusterType
from paas_wl.cluster.models import APIServer, Cluster, IngressConfig


def build_default_cluster():
    from tests.conftest import CLUSTER_NAME_FOR_TESTING

    cluster = Cluster(
        name=CLUSTER_NAME_FOR_TESTING,
        region=settings.FOR_TESTS_DEFAULT_REGION,
        is_default=True,
        ingress_config=cattr.structure(
            {
                "app_root_domains": [{"name": "example.com"}],
                "sub_path_domains": [{"name": "example.com"}],
                "default_ingress_domain_tmpl": "%s.unittest.com",
                "frontend_ingress_ip": "0.0.0.0",
                "port_map": {"http": "80", "https": "443"},
            },
            IngressConfig,
        ),
        annotations={
            "bcs_cluster_id": "",
            "bcs_project_id": "",
        },
        ca_data=settings.FOR_TESTS_CLUSTER_CONFIG["ca_data"],
        cert_data=settings.FOR_TESTS_CLUSTER_CONFIG["cert_data"],
        key_data=settings.FOR_TESTS_CLUSTER_CONFIG["key_data"],
        token_value=settings.FOR_TESTS_CLUSTER_CONFIG["token_value"],
        feature_flags=ClusterFeatureFlag.get_default_flags_by_cluster_type(ClusterType.NORMAL),
    )
    apiserver = APIServer(
        host=settings.FOR_TESTS_CLUSTER_CONFIG["url"],
        cluster=cluster,
        overridden_hostname=settings.FOR_TESTS_CLUSTER_CONFIG["force_domain"],
    )
    return cluster, apiserver


@contextmanager
def mock_cluster_service(ingress_config: Optional[Dict] = None, replaced_ingress_config: Optional[Dict] = None):
    """Replace the original ClusterHelper class to return fake cluster in memory"""
    cluster, _ = build_default_cluster()
    new_ingress_config = cattr.unstructure(cluster.ingress_config)
    if ingress_config is not None:
        new_ingress_config.update(ingress_config)
    if replaced_ingress_config is not None:
        new_ingress_config = replaced_ingress_config
    cluster.ingress_config = cattr.structure(new_ingress_config, IngressConfig)

    def get_cluster_by_name(cluster_name):
        if cluster_name != cluster.name:
            raise Cluster.DoesNotExist
        return cluster

    def has_cluster(cluster_name):
        return cluster.name == cluster_name

    with mock.patch("paas_wl.cluster.shim.RegionClusterService.list_clusters", return_value=[cluster]), mock.patch(
        "paas_wl.cluster.shim.RegionClusterService.get_default_cluster", return_value=cluster
    ), mock.patch(
        "paas_wl.cluster.shim.RegionClusterService.get_cluster_by_name", side_effect=get_cluster_by_name
    ), mock.patch(
        "paas_wl.cluster.shim.RegionClusterService.has_cluster", side_effect=has_cluster
    ), mock.patch(
        "paas_wl.cluster.shim.EnvClusterService.get_cluster", return_value=cluster
    ), mock.patch(
        "paas_wl.cluster.shim.EnvClusterService.get_env_cluster_name", return_value=cluster.name
    ), mock.patch(
        "paas_wl.cluster.shim.EnvClusterService.bind_cluster"
    ):
        yield


@contextmanager
def replace_cluster_service(ingress_config: Optional[Dict] = None, replaced_ingress_config: Optional[Dict] = None):
    """override the configuration for the cluster in db

    :param ingress_config: patch default ingress_config
    :param replaced_ingress_config: replace default ingress_config entirely
    """
    from tests.conftest import CLUSTER_NAME_FOR_TESTING

    cluster = Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)
    history_ingress_config = cattr.unstructure(cluster.ingress_config)
    new_ingress_config = cattr.unstructure(cluster.ingress_config)
    if ingress_config is not None:
        new_ingress_config.update(ingress_config)
    if replaced_ingress_config is not None:
        new_ingress_config = replaced_ingress_config
    cluster.ingress_config = new_ingress_config
    cluster.save()
    yield
    cluster.ingress_config = history_ingress_config
    cluster.save()
