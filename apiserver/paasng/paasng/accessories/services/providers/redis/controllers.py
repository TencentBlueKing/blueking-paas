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

from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.crd import KServiceMonitor, Redis, RedisReplication
from paas_wl.infras.resources.base.kres import KNamespace, KSecret, KService
from paasng.accessories.services.providers.redis.manifests import generate_redis_name

from .manifests import (
    get_external_clb_service_manifest,
    get_redis_password_secret_manifest,
    get_redis_resource,
    get_service_monitor_manifest,
)
from .schemas import RedisInstanceConfig, RedisPlanConfig


class RedisInstanceController:
    """Redis 实例控制器"""

    plan_config: RedisPlanConfig
    instance_config: RedisInstanceConfig
    namespace: str

    def __init__(self, plan_config: RedisPlanConfig, instance_config: RedisInstanceConfig, namespace: str):
        self.plan_config = plan_config
        self.instance_config = instance_config
        self.namespace = namespace
        self.client = get_client_by_cluster_name(self.instance_config.cluster_name)
        self.KRedis = self._get_redis_kresource()

    def _get_redis_kresource(self):
        if self.plan_config.kind == "Redis":
            return Redis
        return RedisReplication

    def _ensure_namespace(self, max_wait_seconds: int = 15) -> bool:
        """确保命名空间存在, 如果命名空间不存在, 那么将创建一个 Namespace 和 ServiceAccount

        :param max_wait_seconds: 等待 ServiceAccount 就绪的时间
        :return: whether an namespace was created.
        """
        namespace_client = KNamespace(self.client)
        _, created = namespace_client.get_or_create(name=self.namespace)
        if created:
            namespace_client.wait_for_default_sa(namespace=self.namespace, timeout=max_wait_seconds)
        return created

    def _deploy_redis_service_monitor(self):
        """创建 Redis 服务监控"""
        if not self.plan_config.monitor:
            return

        manifest = get_service_monitor_manifest()
        KServiceMonitor(self.client, api_version=manifest["apiVersion"]).create(
            name="svc-redis-prometheus-monitoring", body=manifest, namespace=self.namespace
        )

    def _deploy_external_clb_service(self):
        """创建 Redis 服务"""
        manifest = get_external_clb_service_manifest(self.plan_config, self.instance_config)
        KService(self.client).create(
            name=f"{generate_redis_name()}-external-clb-service", body=manifest, namespace=self.namespace
        )

    def _deploy_redis_password_secret(self):
        """创建 Redis 密码 Secret"""
        manifest = get_redis_password_secret_manifest(self.instance_config.password)
        KSecret(self.client).create(name="redis-secret", body=manifest, namespace=self.namespace)

    def _deploy_redis_resource(self):
        """创建 Redis 实例资源(Redis CRD Instance)"""
        manifest = get_redis_resource(self.plan_config).to_deployable()
        self.KRedis(self.client, api_version=manifest["apiVersion"]).create(
            name=generate_redis_name(), body=manifest, namespace=self.namespace
        )

    def create(self):
        """创建 Redis 实例"""
        self._ensure_namespace()
        self._deploy_redis_password_secret()
        self._deploy_redis_resource()
        self._deploy_external_clb_service()
        self._deploy_redis_service_monitor()

    def delete(self):
        """删除 namespace 以删除所有资源"""
        KNamespace(self.client).delete(self.namespace)
