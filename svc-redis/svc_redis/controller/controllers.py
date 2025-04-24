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

import logging
import time
from abc import ABC, abstractmethod

import redis

from svc_redis.cluster.models import TencentCLBListener
from svc_redis.resources.base.base import get_client_by_cluster_name
from svc_redis.resources.base.crd import KServiceMonitor, Redis, RedisReplication
from svc_redis.resources.base.kres import KNamespace, KSecret, KService
from svc_redis.vendor.redis_crd.constants import DEFAULT_REDIS_PORT, RedisType

from .entities import RedisEndpoint, RedisInstanceCredential, RedisPlanConfig
from .exceptions import RedisConnectionFailed
from .manifests import (
    generate_redis_name,
    get_external_tencent_clb_service_manifest,
    get_redis_password_secret_manifest,
    get_redis_resource,
    get_service_monitor_manifest,
)

logger = logging.getLogger(__name__)


class RedisInstanceController:
    """Redis 实例控制器"""

    def __init__(self, plan_config: RedisPlanConfig, namespace: str):
        self.plan_config = plan_config
        self.namespace = namespace
        self.client = get_client_by_cluster_name(self.plan_config.cluster_name)
        self.KRedis = self._get_redis_kresource()

    def create(self) -> RedisInstanceCredential:
        """
        创建 Redis 实例

        主要流程：
        1. 创建 namespace
        2. 创建 Redis 密码凭证对应的 Secret 资源
        3. 创建 Redis 实例资源
        4. 创建 Redis 服务资源
        5. 检测 Redis 服务是否就绪
        """
        self._ensure_namespace()
        password = self._deploy_redis_password_secret()
        self._deploy_redis_resource()
        endpoint = self._deploy_and_get_endpoint()
        self._deploy_redis_service_monitor()
        credential = RedisInstanceCredential(
            host=endpoint.host,
            port=endpoint.port,
            password=password,
        )
        self._check_redis_status(credential)
        return credential

    def delete(self, credential: RedisInstanceCredential):
        """删除 namespace 以删除所有资源"""
        # 删除 Redis 实例资源
        KNamespace(self.client).delete(self.namespace)
        self._recycle_endpoint(credential)

    def _get_redis_kresource(self):
        if self.plan_config.type == RedisType.REDIS.value:
            return Redis
        elif self.plan_config.type == RedisType.REDIS_REPLICATION.value:
            return RedisReplication
        else:
            raise ValueError(f"Unsupported Redis type: {self.plan_config.type}")

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

    def _deploy_and_get_endpoint(self) -> RedisEndpoint:
        """创建 Redis 服务并且返回 endpoint"""
        exporter = ServiceExporterFactory.create_exporter(
            self.plan_config.service_export_type, self.plan_config.cluster_name
        )
        return exporter.deploy_and_get_endpoint(self.plan_config.type, self.namespace)

    def _deploy_redis_password_secret(self) -> str:
        """创建 Redis 密码 Secret"""
        from paas_service.utils import generate_password

        password = generate_password()
        manifest = get_redis_password_secret_manifest(password)
        KSecret(self.client).create(name="redis-secret", body=manifest, namespace=self.namespace)
        return password

    def _deploy_redis_resource(self):
        """创建 Redis 实例资源(Redis CRD Instance)"""
        manifest = get_redis_resource(self.plan_config).to_deployable()
        self.KRedis(self.client, api_version=manifest["apiVersion"]).create(
            name=generate_redis_name(), body=manifest, namespace=self.namespace
        )

    def _recycle_endpoint(self, credential: RedisInstanceCredential):
        exporter = ServiceExporterFactory.create_exporter(
            self.plan_config.service_export_type, self.plan_config.cluster_name
        )
        endpoint = RedisEndpoint(
            host=credential.host,
            port=credential.port,
        )
        return exporter.recycle_endpoint(endpoint)

    def _check_redis_status(self, credential: RedisInstanceCredential, max_attempts=60, retry_interval=10):
        """
        检查 Redis 连接状态

        :param credential: Redis 实例凭证
        :param max_attempts: 最大重试次数
        :param retry_interval: 重试间隔时间（秒）
        """
        for attempt in range(1, max_attempts + 1):
            try:
                r = redis.Redis(
                    host=credential.host,
                    port=credential.port,
                    password=credential.password,
                    decode_responses=True,
                    # 非单体模式下，需要等全部就绪才可以提供服务
                    # 但是会先创建与 master 的连接，因此需要设置较长的超时时间
                    socket_timeout=max_attempts * retry_interval,
                    socket_connect_timeout=max_attempts * retry_interval,
                )
                if r.ping():
                    return
            except redis.ConnectionError as e:
                if attempt < max_attempts:
                    logger.info(f"Redis({credential.host}:{credential.port}) 连接失败, {retry_interval} 秒后重试")
                    time.sleep(retry_interval)
                else:
                    raise RedisConnectionFailed("Redis Connection Failed") from e
            except Exception as e:
                raise RedisConnectionFailed("Redis Connection Failed") from e


class ServiceExporter(ABC):
    """服务暴露策略接口"""

    @abstractmethod
    def deploy_and_get_endpoint(self, redis_type: str, namespace: str) -> RedisEndpoint:
        """获取 endpoint"""

    @abstractmethod
    def recycle_endpoint(self, endpoint: RedisEndpoint):
        """回收 endpoint"""


class ClusterDNSServiceExporter(ServiceExporter):
    """集群内访问策略（ClusterDNS）"""

    def deploy_and_get_endpoint(self, redis_type: str, namespace: str) -> RedisEndpoint:
        # 不需要额外部署服务，由 redis-operator 自动创建
        service_name = generate_redis_name()
        if redis_type == RedisType.REDIS_REPLICATION.value:
            service_name = f"{service_name}-master"

        return RedisEndpoint(
            host=f"{service_name}.{namespace}.svc.cluster.local",
            port=DEFAULT_REDIS_PORT,
        )

    def recycle_endpoint(self, endpoint: RedisEndpoint):
        """会随着 namespace 删除回收，不需要额外操作"""


class TencentCLBServiceExporter(ServiceExporter):
    """腾讯云CLB暴露策略（LoadBalancer）"""

    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name
        self.client = get_client_by_cluster_name(cluster_name)

    def deploy_and_get_endpoint(self, redis_type: str, namespace: str) -> RedisEndpoint:
        endpoint = TencentCLBListener.objects.acquire_by_cluster_name(self.cluster_name)
        try:
            manifest = get_external_tencent_clb_service_manifest(
                redis_type=redis_type, clb_id=endpoint.clb_id, clb_port=endpoint.port
            )
            KService(self.client).create(
                name=f"{generate_redis_name()}-external-clb-service", body=manifest, namespace=namespace
            )
        except Exception:
            # 如果创建失败，释放端点
            endpoint.release()
            raise

        return RedisEndpoint(
            host=endpoint.vip,
            port=endpoint.port,
        )

    def recycle_endpoint(self, endpoint: RedisEndpoint):
        """回收"""
        TencentCLBListener.objects.release(self.cluster_name, endpoint.host, endpoint.port)


class ServiceExporterFactory:
    """服务暴露"""

    @staticmethod
    def create_exporter(
        export_type: str,
        cluster_name: str = None,
    ) -> ServiceExporter:
        """
        根据类型创建对应的Exporter
        :param export_type: 暴露类型（ClusterDNS/TencentCLB）
        :param cluster_name: K8S 集群名称
        """
        if export_type == "ClusterDNS":
            return ClusterDNSServiceExporter()
        elif export_type == "TencentCLB":
            return TencentCLBServiceExporter(cluster_name)
        else:
            raise ValueError(f"Unknown service export type: {export_type}")
