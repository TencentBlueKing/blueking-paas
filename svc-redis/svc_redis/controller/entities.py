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

from typing import Dict, Literal

from pydantic import BaseModel, ConfigDict, model_validator

ResourcePresetName = Literal["512", "1G", "2G"]


class RedisResourcesConfig(BaseModel):
    """套餐资源配额
    常规方案用 preset，特殊方案同时写 requests/limits，也可在 preset 上叠加一侧，详情见 README.md"""

    model_config = ConfigDict(extra="forbid")

    preset: ResourcePresetName | None = None
    # 任意 K8s 资源名，便于后续扩展 hugepages 等
    requests: Dict[str, str] | None = None
    limits: Dict[str, str] | None = None

    @model_validator(mode="after")
    def validate_quota(self):
        if self.preset is not None:
            return self
        if self.requests and self.limits:
            return self
        raise ValueError("resources 必须配置 preset，或同时提供 requests 与 limits")


class RedisPlanConfig(BaseModel):
    """Redis 计划配置"""

    type: Literal["Redis", "RedisReplication"] = "Redis"
    redis_version: str
    # 部署集群
    cluster_name: str
    persistent_storage: bool = False
    monitor: bool = False
    resources: RedisResourcesConfig
    service_export_type: Literal["TencentCLB", "ClusterDNS"] = "ClusterDNS"


class RedisInstanceCredential(BaseModel):
    """Redis 实例配置"""

    host: str
    port: int
    password: str


class RedisEndpoint(BaseModel):
    """Redis 实例 Endpoint 配置"""

    host: str
    port: int
