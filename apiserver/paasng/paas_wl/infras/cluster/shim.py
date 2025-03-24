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

from typing import TYPE_CHECKING, Dict

from paas_wl.infras.cluster.allocator import ClusterAllocator
from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.models import Cluster
from paasng.platform.applications.constants import AppEnvironment
from paasng.platform.modules.constants import ExposedURLType

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application, ModuleEnvironment


def get_exposed_url_type(application: "Application", cluster_name: str | None = None) -> ExposedURLType:
    """Get the exposed url type."""
    if cluster_name:
        cluster = Cluster.objects.get(name=cluster_name)
    else:
        ctx = AllocationContext(
            tenant_id=application.tenant_id,
            region=application.region,
            environment=AppEnvironment.PRODUCTION,
        )
        cluster = ClusterAllocator(ctx).get_default()

    return ExposedURLType(cluster.exposed_url_type)


class EnvClusterService:
    """EnvClusterService provide interface for managing the cluster info of given env"""

    def __init__(self, env: "ModuleEnvironment"):
        self.env = env

    def get_cluster(self) -> Cluster:
        """get the cluster bound to the env, if no specific cluster is bound, return default cluster"""
        return Cluster.objects.get(name=self.get_cluster_name())

    def get_cluster_name(self) -> str:
        """get the cluster bound to the env, if no specific cluster is bound, return default cluster name
        this function will not check if the cluster actually exists.
        """
        wl_app = self.env.wl_app

        if cluster_name := wl_app.latest_config.cluster:
            return cluster_name

        ctx = AllocationContext.from_module_env(self.env)
        return ClusterAllocator(ctx).get_default().name

    def bind_cluster(self, cluster_name: str | None, operator: str | None = None):
        """bind `env` to cluster named `cluster_name`, if cluster_name is not given, use default cluster

        :raises: Cluster.DoesNotExist if cluster not found
        """
        wl_app = self.env.wl_app

        if cluster_name:
            cluster = Cluster.objects.get(name=cluster_name)
        else:
            ctx = AllocationContext.from_module_env(self.env)
            # 支持带操作人的集群分配
            if operator:
                ctx.username = operator

            cluster = ClusterAllocator(ctx).get_default()

        # bind cluster to wl_app
        cfg = wl_app.latest_config
        cfg.cluster = cluster.name
        cfg.mount_log_to_host = cluster.has_feature_flag(
            ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST,
        )
        cfg.save()


def get_app_prod_env_cluster(app: "Application") -> Cluster:
    """获取默认模块生产环境应用使用的集群名称

    FIXME：理论上这个方法不该存在，应用的每个模块-环境都可能部署到不同的集群中，只检查默认模块的 prod 环境是不够的
    相关讨论：https://github.com/TencentBlueKing/blueking-paas/pull/1932#discussion_r1974682390
    """
    env = app.get_default_module().envs.get(environment=AppEnvironment.PRODUCTION)
    return EnvClusterService(env).get_cluster()


def get_app_cluster_names(app: "Application") -> Dict[str, str]:
    """获取默认模块各环境应用使用的集群名称

    :param app: 应用对象
    :return: {环境: 集群名称}
    """
    return {env.environment: EnvClusterService(env).get_cluster_name() for env in app.get_default_module().envs.all()}
