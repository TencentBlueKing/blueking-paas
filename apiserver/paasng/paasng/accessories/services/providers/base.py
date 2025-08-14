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
from abc import ABCMeta, abstractmethod
from typing import ClassVar, Dict, Optional, Set

from django.db import transaction
from django.utils.translation import gettext as _

from paasng.accessories.services.exceptions import ResourceNotEnoughError
from paasng.accessories.services.models import InstanceData, PreCreatedInstance
from paasng.accessories.services.utils import gen_addons_cert_mount_path

logger = logging.getLogger(__name__)


class BaseProvider(metaclass=ABCMeta):
    display_name: ClassVar[str]
    protected_keys: ClassVar[Set] = set()

    @abstractmethod
    def __init__(self, config: Dict):
        raise NotImplementedError

    @abstractmethod
    def create(self, params: Dict) -> InstanceData:
        raise NotImplementedError

    @abstractmethod
    def delete(self, instance_data: InstanceData) -> None:
        raise NotImplementedError

    @abstractmethod
    def patch(self, params: Dict) -> None:
        raise NotImplementedError

    @abstractmethod
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

            creds = json.loads(instance.credentials)
            # 兼容不同格式的历史数据
            if isinstance(instance.config, str):
                cfg = json.loads(instance.config)
            else:
                cfg = instance.config

            tls = cfg.get("tls", {})
            provider_name = instance.plan.service.provider_name
            # 如果实例配置中有证书，则在凭证部分中添加挂载证书的路径
            # 证书内容会在部署时候以 Secret 形式挂载到容器中
            ca, cert, cert_key = tls.get("ca"), tls.get("cert"), tls.get("key")
            if ca:
                creds["ca"] = gen_addons_cert_mount_path(provider_name, "ca.crt")

            if cert and cert_key:
                creds["cert"] = gen_addons_cert_mount_path(provider_name, "tls.crt")
                creds["cert_key"] = gen_addons_cert_mount_path(provider_name, "tls.key")

            # 兼容各类 True 的情况
            if tls.get("insecure_skip_verify") in [True, "true", "True"]:
                creds["insecure_skip_verify"] = "true"

            return InstanceData(
                credentials=creds,
                config={
                    "__pk__": str(instance.pk),
                    "is_pre_created": True,
                    "provider_name": provider_name,
                    "enable_tls": bool(ca or cert or cert_key),
                    "recyclable": cfg.get("recyclable", False),
                },
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

    def patch(self, params: Dict) -> None:
        raise NotImplementedError

    def stats(self, resource):
        raise NotImplementedError
