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

"""Resource Definition of `BkApplication` kind.

Use `pydantic` to get good JSON-Schema support, which is essential for CRD.
https://ot-redis-operator.netlify.app/docs/crd-reference/redis-api/#redisredisopstreelabsinv1beta2
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from paas_wl.utils.text import DNS_SAFE_PATTERN

from .constants import *


class ObjectMetadata(BaseModel):
    """Kubernetes Metadata"""

    # See https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    name: str = Field(..., regex=DNS_SAFE_PATTERN, max_length=253)
    annotations: Dict[str, str] = Field(default_factory=dict)
    generation: int = Field(default=0)


class ResourceRequirements(BaseModel):
    limits: Optional[Dict[str, str]] = None
    requests: Optional[Dict[str, str]] = None


class RedisSecret(BaseModel):
    name: str
    key: str


class KubernetesConfig(BaseModel):
    # Redis Image 与 Operator Version 版本兼容性参考：
    # https://github.com/OT-CONTAINER-KIT/redis-operator?tab=readme-ov-file#image-compatibility
    image: str = f"{DEFAULT_REDIS_REPOSITORY}:{DEFAULT_REDIS_TAG}"
    imagePullPolicy: str = "IfNotPresent"
    resources: Optional[ResourceRequirements] = None
    redisSecret: Optional[RedisSecret] = None


class Storage(BaseModel):
    storage: str = DEFAULT_PERSISTENT_STORAGE_SIZE


class StorageResourceRequests(BaseModel):
    requests: Storage


class VolumeClaimSpec(BaseModel):
    accessModes: List[str] = ["ReadWriteOnce"]
    resources: StorageResourceRequests
    storageClassName: Optional[str] = None


class VolumeClaimTemplate(BaseModel):
    spec: VolumeClaimSpec


class StorageSpec(BaseModel):
    volumeClaimTemplate: VolumeClaimTemplate


class RedisExporterEnvVar(BaseModel):
    name: str
    value: str


class RedisExporter(BaseModel):
    enabled: bool = False
    # Exporter Image 与 Operator Version 版本兼容性参考：
    # https://github.com/OT-CONTAINER-KIT/redis-operator?tab=readme-ov-file#image-compatibility
    image: str = DEFAULT_REDIS_EXPORTER_IMAGE
    imagePullPolicy: str = "IfNotPresent"
    resources: Optional[ResourceRequirements] = None
    env: Optional[List[RedisExporterEnvVar]] = None


class RedisReplicationSpec(BaseModel):
    clusterSize: int = DEFAULT_CLUSTER_SIZE
    kubernetesConfig: KubernetesConfig = Field(default_factory=KubernetesConfig)
    redisExporter: Optional[RedisExporter] = None
    storage: Optional[StorageSpec] = None


class RedisSpec(BaseModel):
    kubernetesConfig: KubernetesConfig = Field(default_factory=KubernetesConfig)
    redisExporter: Optional[RedisExporter] = None
    storage: Optional[StorageSpec] = None


class RedisReplicationResource(BaseModel):
    """RedisReplication resource"""

    apiVersion: str = ApiVersion.V1BETA2.value
    kind: Literal["RedisReplication"] = "RedisReplication"
    metadata: ObjectMetadata
    spec: RedisReplicationSpec

    def to_deployable(self) -> Dict:
        """Return the deployable manifest, excluding None values and status"""
        result = self.dict(exclude_none=True, exclude={"status"})
        result["metadata"].pop("generation", None)
        return result


class RedisResource(BaseModel):
    """Redis resource"""

    apiVersion: str = ApiVersion.V1BETA2.value
    kind: Literal["Redis"] = "Redis"
    metadata: ObjectMetadata
    spec: RedisSpec

    def to_deployable(self) -> Dict:
        """Return the deployable manifest, excluding None values and status"""
        result = self.dict(exclude_none=True, exclude={"status"})
        result["metadata"].pop("generation", None)
        return result
