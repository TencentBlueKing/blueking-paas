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

from pathlib import Path

import pytest
import yaml
from kubernetes.client.apis import VersionApi
from kubernetes.utils.create_from_yaml import create_from_yaml_single_item

from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from tests.paas_wl.e2e.ingress.utils import (
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
def _setup_cluster(cluster):
    # ingress-controller == 1.0.0 必须使用正则表达式
    cluster.feature_flags[ClusterFeatureFlag.INGRESS_USE_REGEX] = True
    cluster.save()


@pytest.fixture(scope="module", autouse=True)
def _setup_ingress_nginx_controller(skip_if_configuration_not_ready, namespace_maker, k8s_client, ingress_nginx_ns):
    k8s_version = VersionApi(k8s_client).get_code()
    # k8s 1.8 只起了 apiserver 模拟测试, 无法进行集成测试
    if (int(k8s_version.major), int(k8s_version.minor)) < (1, 19):
        pytest.skip("ingress-nginx-controller(1.0.0) do not support k8s <= 1.19")
    if (int(k8s_version.major), int(k8s_version.minor)) >= (1, 23):
        pytest.skip("ingress-nginx-controller(0.22.0) do not support k8s >= 1.23")
    # 创建命名空间
    namespace_maker.make(ingress_nginx_ns)
    try:
        # 下发权限相关的资源
        create_from_yaml_allow_conflict(
            k8s_client, filepath=Path(__file__).parent / "assets/rbac.yaml", namespace=ingress_nginx_ns
        )

        # 下发 ingress-nginx 核心服务相关资源
        workload_contents = yaml.safe_load_all((Path(__file__).parent / "assets/ingress-nginx.yaml").read_text())
        for data in workload_contents:
            create_from_yaml_single_item(k8s_client, data, namespace=ingress_nginx_ns)

        # 下发 webhook 相关资源
        create_from_yaml_allow_conflict(
            k8s_client, filepath=Path(__file__).parent / "assets/webhook.yaml", namespace=ingress_nginx_ns
        )

        # 下发 ingress-class
        create_from_yaml_allow_conflict(
            k8s_client, filepath=Path(__file__).parent / "assets/ingress-class.yaml", namespace=ingress_nginx_ns
        )
        yield
    finally:
        # 卸载 webhook 相关资源
        delete_from_yaml_ignore_exception(
            k8s_client, filepath=Path(__file__).parent / "assets/webhook.yaml", namespace=ingress_nginx_ns
        )

        # 删除权限相关资源
        delete_from_yaml_ignore_exception(
            k8s_client, filepath=Path(__file__).parent / "assets/rbac.yaml", namespace=ingress_nginx_ns
        )
