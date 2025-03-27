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
from abc import ABCMeta, abstractmethod, ABC
from typing import ClassVar, Dict, Optional, Set

from django.db import transaction
from django.utils.translation import gettext as _

from paasng.accessories.services.exceptions import ResourceNotEnoughError
from paasng.accessories.services.models import InstanceData, PreCreatedInstance

logger = logging.getLogger(__name__)


class BaseProvider(metaclass=ABCMeta):
    display_name: ClassVar[str]
    protected_keys: ClassVar[Set] = set()

    def __init__(self, config: Dict):
        raise NotImplementedError

    def create(self, params: Dict) -> InstanceData:
        raise NotImplementedError

    def delete(self, instance_data: InstanceData) -> None:
        raise NotImplementedError

    def patch(self, params: Dict) -> None:
        raise NotImplementedError

    def stats(self, resource):
        """[Deprecated]
        return True, message, {'status': 'ok', 'usage': '100M / 1G'}
        """
        raise NotImplementedError


class ResourcePoolProvider(BaseProvider):
    display_name = "资源池算法(FIFO)"
    instance_credentials_schema: ClassVar[Dict]

    def __init__(self, config: Dict):
        self.plan = config["__plan__"]
        self.recyclable = config.get("recyclable", False)

    def create(self, params: Dict) -> InstanceData:
        with transaction.atomic():
            instance: Optional[PreCreatedInstance] = (
                PreCreatedInstance.objects.select_for_update()
                .filter(plan=self.plan, is_allocated=False)
                .order_by("created")
                .first()
            )
            if instance is None:
                raise ResourceNotEnoughError(_("资源不足, 配置资源实例失败."))
            instance.acquire()
            return InstanceData(
                credentials=json.loads(instance.credentials), config={"__pk__": instance.pk, **instance.config}
            )

    def delete(self, instance_data: InstanceData) -> None:
        """如果实例可回收, 则将实例重新放回资源池."""
        recyclable = self.recyclable or getattr(instance_data, "config", {}).get("recyclable", False)
        if not recyclable:
            return

        pk = instance_data.config.get("__pk__") if instance_data.config else None
        if pk:
            PreCreatedInstance.objects.get(pk=pk).release()
        else:
            # no test cover
            logger.warning("`__pk__` is missing, recreate a new PreCreatedInstance by given credentials and config.")
            PreCreatedInstance.objects.create(
                plan=self.plan,
                credentials=json.dumps(instance_data.credentials),
                config=instance_data.config,
                tenant_id=self.plan.tenant_id,
            )


class BaseManagedResourcePoolProvider(ABC, BaseProvider):
    """基础资源池提供者，使用FIFO算法分配预创建实例"""

    def __init__(self, config: Dict):
        self.plan = config["__plan__"]
        self.recyclable = config.get("recyclable", False)

    def _acquire_pre_created_instance(self) -> 'PreCreatedInstance':
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

    def create(self, params: Dict) -> InstanceData:
        """创建资源实例"""
        with transaction.atomic():
            instance = self._acquire_pre_created_instance()

            try:
                # 尝试申请资源
                credentials = self._apply_for_resource(instance, params)

                # 只有资源申请成功后才标记实例为已分配
                instance.acquire()

                return InstanceData(
                    credentials=credentials,
                    config={"__pk__": instance.pk, **instance.config}
                )
            except Exception as e:
                # 如果资源申请失败，实例保持未分配状态
                logger.error(f"资源申请失败: {str(e)}")
                raise ResourceNotEnoughError(_("资源申请失败")) from e

    @abstractmethod
    def _apply_for_resource(self, instance: PreCreatedInstance, params: Dict) -> Dict:
        """子类必须实现的资源申请方法

        Args:
            instance: 预创建实例
            params: 创建参数

        Returns:
            资源凭证字典
        """
        raise NotImplementedError

    @abstractmethod
    def _release_external_resource(self, instance_data: InstanceData) -> None:
        """子类必须实现的真实资源释放逻辑"""
        raise NotImplementedError

    def _should_recycle(self, instance_data: InstanceData) -> bool:
        """判断是否应该回收资源"""
        return self.recyclable or getattr(instance_data, "config", {}).get("recyclable", False)

    def _handle_missing_pk(self, instance_data: InstanceData) -> None:
        """处理缺少 __pk__ 的情况"""
        logger.warning("`__pk__` missing, recreating PreCreatedInstance")
        PreCreatedInstance.objects.create(
            plan=self.plan,
            credentials=json.dumps(instance_data.credentials),
            config=instance_data.config,
            tenant_id=self.plan.tenant_id,
        )

    def delete(self, instance_data: InstanceData) -> None:
        """如果实例可回收, 则将实例重新放回资源池."""
        try:
            # 回收外部资源
            self._release_external_resource(instance_data)
        except Exception as e:
            logger.error(f"资源释放失败: {str(e)}")
            raise ResourceNotEnoughError(_("资源释放失败")) from e

        if not self._should_recycle(instance_data):
            return

        pk = instance_data.config.get("__pk__")
        if not pk:
            self._handle_missing_pk(instance_data)
            return
