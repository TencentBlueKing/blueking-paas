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
from pathlib import Path

import pytest
import yaml
from kubernetes.client.apis import VersionApi

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.resources.base.kube_client import CoreDynamicClient
from tests.e2e.ingress.utils import (
    IngressNginxReloadChecker,
    create_from_yaml_allow_conflict,
    delete_from_yaml_ignore_exception,
)

_checker = None


@pytest.fixture(scope="module")
def ingress_nginx_reload_checker():
    global _checker
    if _checker is None:
        _checker = IngressNginxReloadChecker()
    return _checker.check_keyword_from_logs


@pytest.fixture(autouse=True)
def setup_cluster(cluster):
    # ingress-controller == 0.21.0 不支持正则表达式
    cluster.feature_flags[ClusterFeatureFlag.INGRESS_USE_REGEX] = False
    cluster.save()


@pytest.fixture(scope="module", autouse=True)
def setup_ingress_nginx_controller(skip_if_configuration_not_ready, namespace_maker, k8s_client, ingress_nginx_ns):
    k8s_version = VersionApi(k8s_client).get_code()
    # k8s 1.8 只起了 apiserver 模拟测试, 无法进行集成测试
    if (int(k8s_version.major), int(k8s_version.minor)) == (1, 8):
        pytest.skip("dummy cluster can't run e2e test")
    if (int(k8s_version.major), int(k8s_version.minor)) >= (1, 22):
        pytest.skip("ingress-nginx-controller(0.21.0) do not support k8s >= 1.22")
    dynamic_client = CoreDynamicClient(k8s_client)
    # 创建命名空间
    namespace_maker.make(ingress_nginx_ns)
    try:
        # 下发权限相关的资源
        create_from_yaml_allow_conflict(
            k8s_client, filepath=Path(__file__).parent / "assets/rbac.yaml", namespace=ingress_nginx_ns
        )

        # 下发 ingress-nginx 工作负载相关资源
        workload_contents = yaml.safe_load_all((Path(__file__).parent / "assets/ingress-nginx.yaml").read_text())
        for data in workload_contents:
            # 使用 DynamicClient 兼容更多的集群版本
            api_resource = dynamic_client.get_preferred_resource(data["kind"])
            data["apiVersion"] = api_resource.group_version
            dynamic_client.create(api_resource, body=data, namespace=ingress_nginx_ns)
        yield
    finally:
        # 删除权限相关资源
        delete_from_yaml_ignore_exception(
            k8s_client, filepath=Path(__file__).parent / "assets/rbac.yaml", namespace=ingress_nginx_ns
        )
