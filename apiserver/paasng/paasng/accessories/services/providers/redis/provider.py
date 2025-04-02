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
import json
import logging
from typing import Dict, Optional

from django.db import transaction
from django.utils.translation import gettext as _

from paasng.accessories.services.exceptions import ResourceNotEnoughError
from paasng.accessories.services.models import InstanceData, PreCreatedInstance
from paasng.accessories.services.providers.base import BaseProvider
from paasng.accessories.services.utils import gen_unique_id

from .controllers import RedisInstanceController
from .exceptions import CreateRedisFailed, ReleaseRedisFailed
from .schemas import RedisInstanceConfig, RedisPlanConfig

logger = logging.getLogger(__name__)


class RedisProvider(BaseProvider):
    display_name = "Redis 通用申请服务"
    """
    Redis 资源处理
    """

    def __init__(self, config: Dict):
        self.plan = config["__plan__"]
        self.recyclable = config.get("recyclable", False)

    def _acquire_pre_created_instance(self) -> "PreCreatedInstance":
        """获取一个预创建实例（不立即标记为已分配）"""
        with transaction.atomic():
            instance: Optional[PreCreatedInstance] = (
                PreCreatedInstance.objects.select_for_update()
                .filter(plan=self.plan, is_allocated=False)
                .order_by("created")
                .first()
            )
            if instance is None:
                raise ResourceNotEnoughError(_("资源不足, 配置资源实例失败."))
            # 不再这里调用 acquire()
            return instance

    def _apply_external_resource(self, instance: PreCreatedInstance, namespace: str):
        """Redis 资源申请"""
        plan_config = RedisPlanConfig(**json.loads(self.plan.config))
        instance_config = RedisInstanceConfig(**json.loads(instance.credentials))
        controller = RedisInstanceController(plan_config, instance_config, namespace)
        controller.create()

    def create(self, params: Dict) -> InstanceData:
        """创建资源实例"""
        with transaction.atomic():
            instance = self._acquire_pre_created_instance()

            try:
                # 创建唯一的 namespace
                preferred_name = str(params.get("engine_app_name"))
                uid = gen_unique_id(preferred_name, namespace="svc-redis")
                # 为了 namespace 更具可读性，添加前缀
                namespace = f"svc-redis-{uid}"
                # 尝试申请资源
                self._apply_external_resource(instance, namespace)

                # 只有资源申请成功后才标记实例为已分配
                instance.acquire()

                return InstanceData(
                    credentials=instance.credentials,
                    config={
                        "__pk__": instance.pk,
                        **instance.config,
                        "namespace": namespace,
                    },
                )
            except Exception as e:
                # 如果资源申请失败，实例保持未分配状态
                logger.exception("资源申请失败")
                raise CreateRedisFailed(_("资源申请失败")) from e

    def _release_external_resource(self, instance_data: InstanceData):
        """Redis 资源释放"""
        if not instance_data.config:
            return
        namespace = str(instance_data.config.get("namespace"))
        plan_config = RedisPlanConfig(**json.loads(self.plan.config))
        instance_config = RedisInstanceConfig(**instance_data.credentials)
        controller = RedisInstanceController(plan_config, instance_config, namespace)
        controller.delete()

    def _should_recycle(self, instance_data: InstanceData) -> bool:
        """判断是否应该回收资源"""
        return self.recyclable or getattr(instance_data, "config", {}).get("recyclable", False)

    def delete(self, instance_data: InstanceData) -> None:
        """如果实例可回收, 则将实例重新放回资源池."""
        try:
            # 回收外部资源
            self._release_external_resource(instance_data)
        except Exception as e:
            logger.exception("资源释放失败")
            raise ReleaseRedisFailed(_("资源释放失败")) from e

        if not self._should_recycle(instance_data):
            return

        if not instance_data.config:
            return

        pk = instance_data.config.get("__pk__")
        if not pk:
            logger.warning("`__pk__` missing, recreating PreCreatedInstance")
            PreCreatedInstance.objects.create(
                plan=self.plan,
                credentials=json.dumps(instance_data.credentials),
                config=instance_data.config,
                tenant_id=self.plan.tenant_id,
            )
            return
