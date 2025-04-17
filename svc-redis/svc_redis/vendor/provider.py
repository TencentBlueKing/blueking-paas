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
from dataclasses import dataclass
from typing import Dict

from paas_service.base_vendor import BaseProvider, InstanceData

from svc_redis.controller.controllers import RedisInstanceController
from svc_redis.controller.schemas import RedisInstanceCredential, RedisPlanConfig
from svc_redis.vendor.utils import gen_unique_id

from .exceptions import CreateRedisFailed, DeleteRedisFailed

logger = logging.getLogger(__name__)


@dataclass
class Provider(BaseProvider):
    """Redis 服务提供商实现类
    使用 Kubernetes Operator 管理 Redis 实例

    属性：
        type: Redis 部署类型 (Redis/RedisReplication)
        redis_version: Redis 版本号 (如 'v6.2.12')
        cluster_name: Kubernetes 集群名称
        memory_size: 内存限制 (如 '2Gi')
        service_export_type: 服务暴露方式 ("TencentCLB", "ClusterDNS")
        persistent_storage: 是否启用持久化存储 (默认 False)
        monitor: 是否启用监控 (默认 False)
    """

    type: str
    redis_version: str
    cluster_name: str
    memory_size: str
    service_export_type: str
    persistent_storage: bool = False
    monitor: bool = False

    SERVICE_NAME = "redis"

    def __post_init__(self):
        self.plan_config = RedisPlanConfig(
            type=self.type,
            redis_version=self.redis_version,
            cluster_name=self.cluster_name,
            memory_size=self.memory_size,
            service_export_type=self.service_export_type,
            persistent_storage=self.persistent_storage,
            monitor=self.monitor,
        )

    def create(self, params: Dict) -> InstanceData:
        """创建 Redis 服务实例

        主要流程：
        1. 生成唯一命名空间
        2. 创建 Redis 资源实例
        3. 返回访问凭证

        :param params: Dict, 由 v3 申请增强服务实例时透传
        engine_app_name: str
        :return: InstanceData
        credentials: 连接凭证 (host, port, password)
        config: {"namespace":"xxx"}
        """
        logger.info("正在创建增强服务实例...")

        # 创建唯一的 namespace
        preferred_name = str(params.get("engine_app_name"))
        uid = gen_unique_id(preferred_name)
        # 为了 namespace 更具可读性，添加前缀
        namespace = f"svc-redis-{uid}"

        try:
            controller = RedisInstanceController(self.plan_config, namespace)
            credential = controller.create()
        except Exception as e:
            # 如果资源申请失败，实例保持未分配状态
            logger.exception("资源申请失败")
            raise CreateRedisFailed("资源申请失败") from e

        return InstanceData(credentials=credential.dict(), config={"namespace": namespace})

    def delete(self, instance_data: InstanceData):
        """删除 Redis 实例

        :param instance_data:
        credentials: 连接凭证 (host, port, password)
        config: {"namespace":"xxx"}
        :return:
        """
        logger.info("正在删除增强服务实例...")
        db_info = instance_data.credentials

        credential = RedisInstanceCredential(host=db_info["host"], port=db_info["port"], password=db_info["password"])
        namespace = str(instance_data.config.get("namespace"))
        try:
            controller = RedisInstanceController(self.plan_config, namespace)
            controller.delete(credential)
        except Exception as e:
            logger.exception("资源释放失败")
            raise DeleteRedisFailed("资源释放失败") from e

    def patch(self, instance_data: InstanceData, params: Dict) -> InstanceData:
        raise NotImplementedError
