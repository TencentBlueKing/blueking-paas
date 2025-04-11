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
from blue_krill.data_types.enum import StrStructuredEnum

# ---------------
# Redis 相关配置
# ---------------

# Redis 默认端口
DEFAULT_REDIS_PORT = 6379
# Redis 默认镜像仓库
DEFAULT_REDIS_REPOSITORY = "quay.io/opstree/redis"
# Redis 默认镜像 TAG
DEFAULT_REDIS_TAG = "v7.0.12"

# Redis 暴露指标默认镜像
DEFAULT_REDIS_EXPORTER_IMAGE = "quay.io/opstree/redis-exporter:v1.44.0"
# Redis 暴露指标默认端口
REDIS_EXPORTER_PORT = 9121
# Redis 暴露指标默认名称
REDIS_EXPORTER_PORT_NAME = "redis-exporter"

# 持久存储默认大小
DEFAULT_PERSISTENT_STORAGE_SIZE = "10Gi"

# Redis 集群默认大小
DEFAULT_CLUSTER_SIZE = 3


class ApiVersion(StrStructuredEnum):
    """Redis CRD API version"""

    V1BETA2 = "redis.redis.opstreelabs.in/v1beta2"


class RedisType(StrStructuredEnum):
    """Redis 资源类型的枚举定义"""

    REDIS = "Redis"
    REDIS_REPLICATION = "RedisReplication"
