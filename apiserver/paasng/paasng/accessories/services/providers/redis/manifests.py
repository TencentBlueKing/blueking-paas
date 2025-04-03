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

from abc import ABC, abstractmethod
from typing import List, Union

from django.conf import settings

from paas_wl.bk_app.addons_services.redis import crds
from paas_wl.bk_app.addons_services.redis.constants import (
    DEFAULT_REDIS_EXPORTER_IMAGE,
    DEFAULT_REDIS_PORT,
    DEFAULT_REDIS_REPOSITORY,
    REDIS_EXPORTER_PORT_NAME,
    ApiVersion,
)

from .schemas import RedisInstanceConfig, RedisPlanConfig


class ManifestConstructor(ABC):
    """Construct the manifest for bk_app model, it is usually only responsible for a small part of the manifest."""

    @abstractmethod
    def apply_to(
        self, model_res: Union["crds.RedisResource", "crds.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        """Apply current constructor to the model resource object.
        :raise ManifestConstructorError: Unable to apply current constructor due to errors.
        """
        raise NotImplementedError()


class RedisVersionManifestConstructor(ManifestConstructor):
    """Construct the redis version."""

    def apply_to(
        self, model_res: Union["crds.RedisResource", "crds.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        redis_version = plan_config.redis_version
        model_res.spec.kubernetesConfig.image = f"{DEFAULT_REDIS_REPOSITORY}:{redis_version}"


class PasswordManifestConstructor(ManifestConstructor):
    """Construct the redis version."""

    def apply_to(
        self, model_res: Union["crds.RedisResource", "crds.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        model_res.spec.kubernetesConfig.redisSecret = crds.RedisSecret(name="redis-secret", key="password")


class MonitorManifestConstructor(ManifestConstructor):
    """Construct the monitor config."""

    def apply_to(
        self, model_res: Union["crds.RedisResource", "crds.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        monitor = plan_config.monitor
        if monitor:
            model_res.spec.redisExporter = crds.RedisExporter(
                enabled=True, image=DEFAULT_REDIS_EXPORTER_IMAGE, resources=self._get_default_resources()
            )

    def _get_default_resources(self) -> crds.ResourceRequirements:
        return crds.ResourceRequirements(
            requests={"cpu": "500m", "memory": "512Mi"}, limits={"cpu": "500m", "memory": "512Mi"}
        )


class ResourceManifestConstructor(ManifestConstructor):
    """Construct the resource config."""

    def apply_to(
        self, model_res: Union["crds.RedisResource", "crds.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        memory_limit = plan_config.memory_size
        model_res.spec.kubernetesConfig.resources = self._get_resources(memory_limit)

    def _get_resources(self, memory_limit: str) -> crds.ResourceRequirements:
        """根据内存限制自动计算合理的资源请求和限制

        Args:
            memory_limit: 必须是 2Gi/4Gi/8Gi

        Returns:
            符合Kubernetes最佳实践的ResourceRequirements
        """
        mem_int = int(memory_limit.removesuffix("Gi"))

        return crds.ResourceRequirements(
            requests={
                # 每 GB 内存配 0.25 CPU(cpu limits 的一半)
                "cpu": f"{mem_int * 250}m",
                # 请求值为limit的一半
                "memory": f"{mem_int // 2}Gi",
            },
            limits={
                # 每GB内存配0.5 CPU
                "cpu": f"{mem_int * 500}m",
                "memory": memory_limit,
            },
        )


class PersistentStorageManifestConstructor(ManifestConstructor):
    """Construct the persistent storage config."""

    def apply_to(
        self, model_res: Union["crds.RedisResource", "crds.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        if plan_config.persistent_storage:
            storage_spec = crds.StorageSpec(
                volumeClaimTemplate=crds.VolumeClaimTemplate(
                    spec=crds.VolumeClaimSpec(
                        accessModes=["ReadWriteOnce"],
                        storageClassName=settings.DEFAULT_PERSISTENT_STORAGE_CLASS_NAME,
                        resources=crds.StorageResourceRequests(requests=crds.Storage(storage="10Gi")),
                    )
                )
            )
            model_res.spec.storage = storage_spec


def create_redis_base_resource(redis_type: str, name: str):
    metadata = crds.ObjectMetadata(name=name)

    if redis_type == "Redis":
        return crds.RedisResource(
            apiVersion=ApiVersion.V1BETA2.value,
            metadata=metadata,
            spec=crds.RedisSpec(),
        )
    elif redis_type == "RedisReplication":
        return crds.RedisReplicationResource(
            apiVersion=ApiVersion.V1BETA2.value,
            metadata=metadata,
            spec=crds.RedisReplicationSpec(),
        )
    else:
        raise ValueError(f"Unsupported Redis type: {redis_type}")


def generate_redis_name():
    return "svc-redis"


def get_redis_resource(plan_config: RedisPlanConfig) -> crds.RedisReplicationResource:
    builders: List[ManifestConstructor] = [
        RedisVersionManifestConstructor(),
        PasswordManifestConstructor(),
        MonitorManifestConstructor(),
        ResourceManifestConstructor(),
        PersistentStorageManifestConstructor(),
    ]
    obj = create_redis_base_resource(plan_config.kind, generate_redis_name())
    for builder in builders:
        builder.apply_to(obj, plan_config)
    return obj


def get_redis_password_secret_manifest(password: str) -> dict:
    return {
        "apiVersion": "v1",
        "metadata": {
            "name": "redis-secret",
        },
        "type": "Opaque",
        "stringData": {
            "password": password,
        },
    }


def get_service_monitor_manifest() -> dict:
    endpoint = {
        "port": REDIS_EXPORTER_PORT_NAME,
        "interval": "30s",
        "scrapeTimeout": "10s",
    }
    match_labels = {"app": generate_redis_name()}

    return {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "ServiceMonitor",
        "metadata": {
            "name": "svc-redis-prometheus-monitoring",
        },
        "spec": {
            "endpoints": endpoint,
            "selector": {"matchLabels": match_labels},
        },
    }


def get_external_clb_service_manifest(plan_config: RedisPlanConfig, instance_config: RedisInstanceConfig) -> dict:
    selector_labels = {
        "app": generate_redis_name(),
    }
    # 如果是主从架构，只有 master 节点才会暴露到外部
    if plan_config.kind == "RedisReplication":
        selector_labels["redis-role"] = "master"

    body = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": f"{generate_redis_name()}-external-clb-service",
            "annotations": {"service.kubernetes.io/tke-existed-lbid": instance_config.clb_id},
        },
        "spec": {
            "ports": [
                {
                    "name": "redis-client",
                    "port": instance_config.port,
                    "targetPort": DEFAULT_REDIS_PORT,
                    "protocol": "TCP",
                }
            ],
            "selector": selector_labels,
            "type": "LoadBalancer",
        },
    }
    return body
