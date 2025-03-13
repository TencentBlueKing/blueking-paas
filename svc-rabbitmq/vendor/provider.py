# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

from django.conf import settings
from paas_service.base_vendor import ArgumentInvalidError, BaseProvider, InstanceData
from paas_service.utils import WRItemList

from .client import Client
from .clusters import Cluster
from .helper import InstanceHelper, Version
from .models import InstanceBill, LimitPolicy, UserPolicy
from .utils import generate_password

logger = logging.getLogger(__name__)


@dataclass
class ProviderPlugin:
    context: "dict"
    client: "Client"
    cluster: "Cluster"
    virtual_host: "str"

    def on_create(self):
        pass

    def on_delete(self):
        pass

    def on_patch(self):
        pass


class UserPolicyProviderPlugin(ProviderPlugin):
    """用户策略插件"""

    def on_create(self):
        policies = self.context.setdefault("policies", [])
        for instance in UserPolicy.objects.filter(enable=True, cluster_id=self.cluster.pk):
            policy: "UserPolicy" = instance.resolved
            policies.append(policy.name)
            self.client.user_policy.create(
                self.virtual_host,
                policy.name,
                {
                    "pattern": policy.pattern,
                    "priority": policy.priority,
                    "apply-to": policy.apply_to,
                    "definition": policy.definitions or {},
                },
            )


class LimitPolicyProviderPlugin(ProviderPlugin):
    """限制策略插件 >= 3.7.0"""

    min_version = Version("3.7.0")

    def on_create(self):
        version = Version(self.cluster.version)
        if version < self.min_version:
            return

        limits = self.context.setdefault("limits", [])
        for instance in LimitPolicy.objects.filter(enable=True, cluster_id=self.cluster.pk):
            policy: "LimitPolicy" = instance.resolved
            limits.append(policy.name)
            self.client.limit_policy.create(self.virtual_host, policy.limit, policy.value)


class DeadLetterRoutingProviderPlugin(ProviderPlugin):
    """配置全局死信路由，生效需要策略配合 >= 2.8.0"""

    min_version = Version("2.8.0")

    def on_create(self):
        version = Version(self.cluster.version)
        if version < self.min_version:
            return

        virtual_host = self.virtual_host
        client = self.client
        context = self.context

        exchange = context.setdefault("dlx-exchange", settings.RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE)
        exchange_type = context.setdefault("dlx-exchange-type", settings.RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE_TYPE)
        durable = context.setdefault("dlx-exchange-durable", settings.RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE_DURABLE)
        client.exchange.declare(
            virtual_host=virtual_host, exchange=exchange, exchange_type=exchange_type, durable=durable
        )

        queue = context.setdefault("dlx-queue", settings.RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE)
        durable = context.setdefault("dlx-queue-durable", settings.RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE_DURABLE)
        client.queue.declare(virtual_host=virtual_host, queue=queue, durable=durable)

        routing_key = context.setdefault("dlx-routing-key", settings.RABBITMQ_DEFAULT_DEAD_LETTER_ROUTING_KEY)
        client.queue.bind(queue=queue, exchange=exchange, virtual_host=virtual_host, routing_key=routing_key)


class AdminAutoPermission(ProviderPlugin):
    """自动加上管理员权限"""

    def on_create(self):
        self.client.user.set_permission(
            username=self.cluster.admin,
            virtual_host=self.virtual_host,
            configure_regex=settings.RABBITMQ_DEFAULT_USER_CONFIGURE_PERMISSIONS,
            write_regex=settings.RABBITMQ_DEFAULT_USER_WRITE_PERMISSIONS,
            read_regex=settings.RABBITMQ_DEFAULT_USER_READ_PERMISSIONS,
        )


PROVIDER_PLUGINS: "List[Type[ProviderPlugin]]" = [
    AdminAutoPermission,
    DeadLetterRoutingProviderPlugin,
]


@dataclass
class Provider(BaseProvider):
    host: Optional[str] = None
    port: Optional[int] = None
    management_api: Optional[str] = None
    admin: Optional[str] = None
    password: Optional[str] = None
    version: Optional[str] = None
    clusters: List = field(default_factory=list)

    def make_instance_name(self, name: "str", uuid: "str") -> "str":
        parts = []
        if settings.INSTANCE_DEFAULT_PREFIX:
            parts.append(settings.INSTANCE_DEFAULT_PREFIX)

        parts.extend(
            [
                name[: settings.INSTANCE_APP_NAME_MAX_LENGTH],
                uuid[: settings.INSTANCE_BILL_ID_MAX_LENGTH],
            ]
        )

        # {prefix}-{name}-{id}
        return "-".join(parts)

    def pick_cluster(self) -> Cluster:
        """pick a single cluster config from available clusters"""
        if not self.clusters:
            assert self.host, "未设置 rabbitmq 服务地址"
            assert self.port, "未设置 rabbitmq 服务端口"
            assert self.management_api, "未设置 rabbitmq 管理地址"
            assert self.admin, "未设置 rabbitmq 管理员用户"
            assert self.password, "未设置 mysql 管理员用户密码"
            assert self.version, "未设置 rabbitmq 版本"
            return Cluster(
                host=self.host,
                port=self.port,
                management_api=self.management_api,
                admin=self.admin,
                password=self.password,
                version=self.version,
            )

        result = WRItemList.from_json(self.clusters).get()
        return Cluster(**result.values)

    def create_instance(
        self, name: "str", bill: "InstanceBill", context: "dict", cluster: "Cluster"
    ) -> "InstanceData":
        """创建实例"""
        context["host"] = cluster.host
        context["port"] = cluster.port
        bill_uid = bill.uuid.hex

        # client 接口是幂等的
        client = Client.from_cluster(cluster)

        instance_name = self.make_instance_name(name, bill_uid)

        # 1. 创建vhost
        virtual_host = context.setdefault("vhost", instance_name)
        client.virtual_host.create(virtual_host)

        # 2. 创建账户
        user = context.setdefault("user", instance_name)
        password = context.setdefault("password", generate_password())
        client.user.create(user, password, settings.RABBITMQ_DEFAULT_USER_TAGS)

        # 3. vhost 授权
        client.user.set_permission(
            username=user,
            virtual_host=virtual_host,
            configure_regex=settings.RABBITMQ_DEFAULT_USER_CONFIGURE_PERMISSIONS,
            write_regex=settings.RABBITMQ_DEFAULT_USER_WRITE_PERMISSIONS,
            read_regex=settings.RABBITMQ_DEFAULT_USER_READ_PERMISSIONS,
        )

        for cls in PROVIDER_PLUGINS:
            plugin = cls(context=context, cluster=cluster, client=client, virtual_host=virtual_host)
            plugin.on_create()

        return InstanceData(
            credentials={
                "host": cluster.host,
                "port": cluster.port,
                "user": user,
                "password": password,
                "vhost": virtual_host,
            },
            config={"bill": bill.uuid.hex},
        )

    def create(self, params: Dict) -> "InstanceData":
        engine_app_name = params.get("engine_app_name")
        if not engine_app_name:
            raise ArgumentInvalidError("engine_app_name is empty")

        # 注意：请不要尝试复用 InstanceBill，由于增强服务默认采用异步删除机制，会导致 vhost 解绑后被重新分配，而后又被定时任务清除的情况出现
        bill = InstanceBill.objects.create(name=engine_app_name, action="create")
        with bill.log_context() as context:  # type: dict
            context["engine_app_name"] = engine_app_name
            cluster = self.pick_cluster()

            try:
                return self.create_instance(engine_app_name, bill, context, cluster)
            except Exception:
                logger.exception("Failed to delete instance")
                raise

    def delete_instance(self, context: "dict", cluster: "Cluster", instance_data: "InstanceData"):
        credentials = instance_data.credentials
        client = Client.from_cluster(cluster)

        # 1. 删除用户
        if not context.setdefault("user_deleted", False):
            user = credentials["user"]
            client.user.delete(user)
            context["user_deleted"] = True

        # 2. 删除 vhost
        virtual_host = credentials["vhost"]
        if not context.setdefault("vhost_deleted", False):
            client.virtual_host.delete(virtual_host)
            context["vhost_deleted"] = True

        for cls in PROVIDER_PLUGINS:
            plugin = cls(context=context, cluster=cluster, client=client, virtual_host=virtual_host)
            plugin.on_delete()

    def delete(self, instance_data: "InstanceData"):
        """删除 RabbitMq 实例

        :param instance_data:
        credentials:
            "host": str,
            "port": str,
            "user": str,
            "password": str,
            "vhost": str,
        config: {}
        :return:
        """
        helper = InstanceHelper(instance_data)
        bill = helper.get_bill()
        bill.action = "delete"

        cluster = self.pick_cluster()
        with bill.log_context() as context:  # type: dict
            try:
                self.delete_instance(context, cluster, instance_data)
            except Exception:
                logger.exception("Failed to delete instance")
                raise

    def patch(self, instance_data: InstanceData, params: Dict) -> InstanceData:
        raise NotImplementedError
