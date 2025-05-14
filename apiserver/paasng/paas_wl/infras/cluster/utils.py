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

from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.entities import AllocationContext, AppImageRegistry
from paas_wl.infras.cluster.models import Cluster, ClusterAppImageRegistry
from paas_wl.infras.cluster.shim import ClusterAllocator


def get_cluster_by_app(app: WlApp) -> Cluster:
    """Get kubernetes cluster by given app

    :param app: WlApp object
    :raise RuntimeError: App has an invalid cluster_name defined
    """
    if app.use_dev_sandbox:
        return get_dev_sandbox_cluster(app)

    cluster_name = app.config_set.latest().cluster
    if not cluster_name:
        return ClusterAllocator(AllocationContext.from_wl_app(app)).get_default()

    try:
        return Cluster.objects.get(name=cluster_name)
    except Cluster.DoesNotExist:
        raise RuntimeError(f"Can not find a cluster called {cluster_name}")


def get_dev_sandbox_cluster(app: WlApp) -> Cluster:
    # 优先使用指定的开发沙箱集群
    if cluster_name := settings.DEV_SANDBOX_CLUSTER:
        try:
            return Cluster.objects.get(name=cluster_name)
        except Cluster.DoesNotExist:
            raise RuntimeError(f"dev sandbox cluster called {cluster_name} no found")

    # 否则使用使用匹配到的的默认集群，注意：
    #  - 功能要求 k8s 版本 >= 1.20.x, 版本过低可能会导致 ingress 等资源出现版本兼容问题
    return ClusterAllocator(AllocationContext.from_wl_app(app)).get_default()


def get_image_registry_by_app(app: WlApp) -> AppImageRegistry:
    """获取 WlApp 使用的镜像仓库信息"""
    cluster = get_cluster_by_app(app)

    # 如果应用绑定的集群，有配置自定义镜像仓库，则应该使用
    if reg := ClusterAppImageRegistry.objects.filter(cluster=cluster).first():
        return AppImageRegistry(
            host=reg.host,
            skip_tls_verify=reg.skip_tls_verify,
            namespace=reg.namespace,
            username=reg.username,
            password=reg.password,
        )

    # 否则使用默认的镜像仓库
    return AppImageRegistry(
        host=settings.APP_DOCKER_REGISTRY_HOST,
        skip_tls_verify=settings.APP_DOCKER_REGISTRY_SKIP_TLS_VERIFY,
        namespace=settings.APP_DOCKER_REGISTRY_NAMESPACE,
        username=settings.APP_DOCKER_REGISTRY_USERNAME,
        password=settings.APP_DOCKER_REGISTRY_PASSWORD,
    )
