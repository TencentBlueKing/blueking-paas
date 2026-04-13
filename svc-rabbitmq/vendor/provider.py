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
from typing import Dict, List, Type

from django.conf import settings
from paas_service.base_vendor import ArgumentInvalidError, BaseProvider, InstanceData
from paas_service.utils import WRItemList
from pydantic import ValidationError

from .client import Client
from .clusters import Cluster
from .helper import InstanceHelper, Version
from .models import Cluster as ClusterModel
from .models import InstanceBill, LimitPolicy, UserPolicy
from .utils import gen_addons_cert_mount_path, generate_password

logger = logging.getLogger(__name__)

# Quorum queues were introduced in RabbitMQ 3.8.0
QUORUM_MIN_VERSION = Version("3.8.0")


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


class HAProviderPlugin(ProviderPlugin):
    """高可用策略插件, 根据使用的 RabbitMQ 版本选择合适的 HA 策略

    - RabbitMQ >= 3.8.0: 直接在 vhost 上设置 default_queue_type=quorum, 使用 Quorum Queues 实现高可用
    - RabbitMQ < 3.8.0: 使用 Classic Mirrored Queues (ha-mode=all)
    """

    # Policy name applied to the vhost for HA
    HA_POLICY_NAME = "bk-ha-policy"

    def _get_mirror_policy(self) -> dict:
        """Build policy definition for classic mirrored queues (< 3.8.0)."""
        return {
            "pattern": ".*",
            "priority": 0,
            "apply-to": "queues",
            "definition": {
                "ha-mode": "all",
                "ha-sync-mode": "automatic",
            },
        }

    def on_create(self):
        if not getattr(settings, "RABBITMQ_HA_POLICY_ENABLED", True):
            logger.info("HA policy is disabled by settings, skipping")
            return

        version = Version(self.cluster.version)
        if version >= QUORUM_MIN_VERSION:
            # RabbitMQ 3.8+: 直接在虚拟主机上设置 default_queue_type, 因为 queue-type 不再是有效的用户策略定义键.
            logger.info(
                "RabbitMQ version %s >= 3.8.0, setting vhost default_queue_type=quorum for vhost %s",
                self.cluster.version,
                self.virtual_host,
            )
            self.client.virtual_host.create(self.virtual_host, default_queue_type="quorum")
        else:
            logger.info(
                "RabbitMQ version %s < 3.8.0, using classic mirror HA policy for vhost %s",
                self.cluster.version,
                self.virtual_host,
            )
            policy = self._get_mirror_policy()
            self.client.user_policy.create(self.virtual_host, self.HA_POLICY_NAME, policy)


class UserPolicyProviderPlugin(ProviderPlugin):
    """用户策略插件"""

    def on_create(self):
        cluster_pk = self.context.get("cluster_pk")
        if not cluster_pk:
            logger.warning("skip user policies because cluster_pk is missing")
            return

        policies = self.context.setdefault("policies", [])
        for instance in UserPolicy.objects.filter(enable=True, cluster_id=cluster_pk):
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

        cluster_pk = self.context.get("cluster_pk")
        if not cluster_pk:
            logger.warning("skip limit policies because cluster_pk is missing")
            return
        limits = self.context.setdefault("limits", [])
        for instance in LimitPolicy.objects.filter(enable=True, cluster_id=cluster_pk):
            policy: "LimitPolicy" = instance.resolved
            limits.append(policy.name)
            self.client.limit_policy.create(self.virtual_host, policy.limit, policy.value)


class DeadLetterRoutingProviderPlugin(ProviderPlugin):
    """配置全局死信路由，生效需要策略配合 >= 2.8.0"""

    min_version = Version("2.8.0")

    def _should_use_quorum(self) -> bool:
        """Check if the cluster version supports quorum queues."""
        version = Version(self.cluster.version)
        return version >= QUORUM_MIN_VERSION

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

        # For RabbitMQ >= 3.8.0, explicitly declare the dead letter queue as quorum type
        # to ensure high availability. The Management HTTP API does not automatically
        # inherit the vhost's default_queue_type setting.
        queue_arguments = {}
        if self._should_use_quorum():
            queue_arguments["x-queue-type"] = "quorum"
            # Quorum queues are always durable, force durable=True
            durable = True
            logger.info(
                "Declaring dead letter queue %s as quorum type for vhost %s",
                queue,
                virtual_host,
            )
        client.queue.declare(virtual_host=virtual_host, queue=queue, durable=durable, arguments=queue_arguments)

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
    HAProviderPlugin,
    UserPolicyProviderPlugin,
    LimitPolicyProviderPlugin,
    DeadLetterRoutingProviderPlugin,
]


@dataclass
class Provider(BaseProvider):
    host: str | None = None
    port: int | None = None
    management_api: str | None = None
    admin: str | None = None
    password: str | None = None
    version: str | None = None
    tls: Dict[str, str] = field(default_factory=dict)
    # clusters 包含多个 RabbitMQ 集群配置
    clusters: List[Dict] = field(default_factory=list)

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

    def resolve_cluster_pk(self, cluster: Cluster) -> int | None:
        """根据集群配置解析出对应的 ClusterModel 主键

        运行时的 Cluster 数据类时从 providor JSON 反序列化而来, 不携带数据库主键,
        但是 UserPolicyProviderPlugin 和 LimitPolicyProviderPlugin 需要 cluster_pk 来查询对应的策略配置
        """
        enabled_clusters = ClusterModel.objects.filter(enable=True)
        mgmt_api = (cluster.management_api or "").rstrip("/")

        if not mgmt_api:
            logger.warning(
                "cluster management_api is empty, cannot resolve cluster_pk accurately, fallback to host/port matching"
            )
            db_cluster = enabled_clusters.filter(host=cluster.host, port=cluster.port).first()
            return db_cluster.pk if db_cluster else None

        for db_cluster in enabled_clusters:
            if (db_cluster.management_api or "").rstrip("/") == mgmt_api:
                return db_cluster.pk

        return None

    def pick_cluster(self) -> Cluster:
        """pick a single cluster config from available clusters"""
        if not self.clusters:
            values = {
                "host": self.host,
                "port": self.port,
                "management_api": self.management_api,
                "admin": self.admin,
                "password": self.password,
                "version": self.version,
                "tls": self.tls,
            }
            try:
                return Cluster(**values)
            except ValidationError as e:
                raise ValueError(f"cluster 配置不正确: {e}")

        result = WRItemList.from_json(self.clusters).get()
        if not result:
            raise ValueError("clusters 列表配置不正确，无法获取集群配置")
        try:
            return Cluster(**result.values)
        except ValidationError as e:
            raise ValueError(f"cluster 配置不正确: {e}")

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

        credentials = {
            "host": cluster.host,
            "port": cluster.port,
            "user": user,
            "password": password,
            "vhost": virtual_host,
        }

        ca = cluster.tls.get("ca")
        cert = cluster.tls.get("cert")
        cert_key = cluster.tls.get("key")

        # 添加证书路径到凭证信息中
        provider_name = "rabbitmq"
        if ca:
            credentials["ca"] = gen_addons_cert_mount_path(provider_name, "ca.crt")

        if cert and cert_key:
            credentials["cert"] = gen_addons_cert_mount_path(provider_name, "tls.crt")
            credentials["cert_key"] = gen_addons_cert_mount_path(provider_name, "tls.key")

        # 兼容各类 True 的情况
        if cluster.tls.get("insecure_skip_verify") in [True, "true", "True"]:
            credentials["insecure_skip_verify"] = "true"

        return InstanceData(
            credentials=credentials,
            config={"bill": bill.uuid.hex, "provider_name": provider_name, "enable_tls": bool(ca or cert or cert_key)},
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
            context["cluster_pk"] = self.resolve_cluster_pk(cluster)
            if context["cluster_pk"] is None:
                logger.warning(
                    "cluster_pk resolve failed: host=%s port=%s management_api=%s",
                    cluster.host,
                    cluster.port,
                    cluster.management_api,
                )

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
