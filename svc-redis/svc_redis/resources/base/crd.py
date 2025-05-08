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

from .kres import BaseKresource


class KServiceMonitor(BaseKresource):
    kind = "ServiceMonitor"


class Redis(BaseKresource):
    """Kubernetes CRD: Redis 单实例资源
    用于定义和管理独立的 Redis 实例"""

    kind = "Redis"


class RedisReplication(BaseKresource):
    """Kubernetes CRD: Redis 主从复制集群
    用于定义 Redis 主从复制架构"""

    kind = "RedisReplication"


class CRD(BaseKresource):
    """Kubernetes CRD: Redis 主从复制集群
    用于定义 Redis 主从复制架构"""

    kind = "CustomResourceDefinition"
