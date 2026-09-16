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

from abc import ABC, abstractmethod
from typing import List, Union

from django.conf import settings

from svc_redis.vendor.redis_crd import crd
from svc_redis.vendor.redis_crd.constants import (
    DEFAULT_REDIS_EXPORTER_IMAGE,
    DEFAULT_REDIS_PORT,
    DEFAULT_REDIS_REPOSITORY,
    REDIS_EXPORTER_PORT_NAME,
    ApiVersion,
    RedisType,
)

from .entities import RedisPlanConfig
from .resource_presets import resolve_plan_resources


class ManifestConstructor(ABC):
    """Construct the manifest for redis model, it is usually only responsible for a small part of the manifest."""

    @abstractmethod
    def apply_to(
        self, model_res: Union["crd.RedisResource", "crd.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        """Apply current constructor to the model resource object.
        :raise ManifestConstructorError: Unable to apply current constructor due to errors.
        """
        raise NotImplementedError


class RedisVersionManifestConstructor(ManifestConstructor):
    """Construct the redis version."""

    def apply_to(
        self, model_res: Union["crd.RedisResource", "crd.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        redis_version = plan_config.redis_version
        model_res.spec.kubernetesConfig.image = f"{DEFAULT_REDIS_REPOSITORY}:{redis_version}"


class PasswordManifestConstructor(ManifestConstructor):
    """Construct the redis password."""

    def apply_to(
        self, model_res: Union["crd.RedisResource", "crd.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        model_res.spec.kubernetesConfig.redisSecret = crd.RedisSecret(name="redis-secret", key="password")


class MonitorManifestConstructor(ManifestConstructor):
    """Construct the monitor config."""

    def apply_to(
        self, model_res: Union["crd.RedisResource", "crd.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        monitor = plan_config.monitor
        if monitor:
            model_res.spec.redisExporter = crd.RedisExporter(
                enabled=True, image=DEFAULT_REDIS_EXPORTER_IMAGE, resources=self._get_default_resources()
            )

    def _get_default_resources(self) -> crd.ResourceRequirements:
        return crd.ResourceRequirements(
            requests={"cpu": "500m", "memory": "512Mi"}, limits={"cpu": "500m", "memory": "512Mi"}
        )


class ResourceManifestConstructor(ManifestConstructor):
    """Construct the resource config."""

    def apply_to(
        self, model_res: Union["crd.RedisResource", "crd.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        resolved = resolve_plan_resources(plan_config)
        model_res.spec.kubernetesConfig.resources = crd.ResourceRequirements(
            requests=resolved.requests, limits=resolved.limits
        )


class PersistentStorageManifestConstructor(ManifestConstructor):
    """Construct the persistent storage config."""

    def apply_to(
        self, model_res: Union["crd.RedisResource", "crd.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        if plan_config.persistent_storage:
            storage_spec = crd.StorageSpec(
                volumeClaimTemplate=crd.VolumeClaimTemplate(
                    spec=crd.VolumeClaimSpec(
                        accessModes=["ReadWriteOnce"],
                        storageClassName=settings.DEFAULT_PERSISTENT_STORAGE_CLASS_NAME,
                        resources=crd.StorageResourceRequests(requests=crd.Storage(storage="10Gi")),
                    )
                )
            )
            model_res.spec.storage = storage_spec


class DisableAdditionalServiceConstructor(ManifestConstructor):
    """禁用单节点 Redis 的 additional Service，减少集群 Service 数量。"""

    def apply_to(
        self, model_res: Union["crd.RedisResource", "crd.RedisReplicationResource"], plan_config: RedisPlanConfig
    ):
        # 目前 redis-operator.opstree 仅支持 kind: Redis 的 svc 削减
        if plan_config.type != RedisType.REDIS.value:
            return
        model_res.spec.kubernetesConfig.service = crd.KubernetesServiceConfig(
            additional=crd.AdditionalServiceConfig(enabled=False)
        )


def create_redis_base_resource(redis_type: str, name: str) -> Union[crd.RedisResource, crd.RedisReplicationResource]:
    metadata = crd.ObjectMetadata(name=name)

    match redis_type:
        case RedisType.REDIS.value:
            return crd.RedisResource(
                apiVersion=ApiVersion.V1BETA2.value,
                metadata=metadata,
                spec=crd.RedisSpec(),
            )
        case RedisType.REDIS_REPLICATION.value:
            return crd.RedisReplicationResource(
                apiVersion=ApiVersion.V1BETA2.value,
                metadata=metadata,
                spec=crd.RedisReplicationSpec(),
            )
        case _:
            raise ValueError(f"Unsupported Redis type: {redis_type}")


def generate_redis_name():
    return "svc-redis"


def get_redis_resource(plan_config: RedisPlanConfig) -> Union["crd.RedisResource", "crd.RedisReplicationResource"]:
    builders: List[ManifestConstructor] = [
        RedisVersionManifestConstructor(),
        PasswordManifestConstructor(),
        MonitorManifestConstructor(),
        ResourceManifestConstructor(),
        PersistentStorageManifestConstructor(),
        DisableAdditionalServiceConstructor(),
    ]
    obj = create_redis_base_resource(plan_config.type, generate_redis_name())
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
            "endpoints": [endpoint],
            "selector": {"matchLabels": match_labels},
        },
    }


def get_external_tencent_clb_service_manifest(redis_type: str, clb_id: str, clb_port: int) -> dict:
    selector_labels = {
        "app": generate_redis_name(),
    }
    # 如果是主从架构，只有 master 节点才会暴露到外部
    if redis_type == RedisType.REDIS_REPLICATION.value:
        selector_labels["redis-role"] = "master"

    body = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": f"{generate_redis_name()}-external-clb-service",
            "annotations": {"service.kubernetes.io/tke-existed-lbid": clb_id},
        },
        "spec": {
            "ports": [
                {
                    "name": "redis-client",
                    "port": clb_port,
                    "targetPort": DEFAULT_REDIS_PORT,
                    "protocol": "TCP",
                }
            ],
            "selector": selector_labels,
            "type": "LoadBalancer",
        },
    }
    return body
