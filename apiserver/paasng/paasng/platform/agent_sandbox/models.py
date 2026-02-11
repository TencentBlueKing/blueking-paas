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

import random
import uuid

from blue_krill.models.fields import EncryptField
from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string

from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator
from paas_wl.workloads.networking.egress.cluster_state import format_nodes_data
from paas_wl.workloads.networking.egress.models import RegionClusterState
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.applications.models import Application
from paasng.utils.models import BkUserField, UuidAuditedModel

from .constants import SandboxStatus
from .exceptions import SandboxAlreadyExists, SandboxCreateError


class SandboxQuerySet(models.QuerySet):
    """沙箱 QuerySet 类"""

    def create(
        self,
        application: Application,
        creator: str,
        snapshot: str,
        snapshot_entrypoint: list | None = None,
        env_vars: dict | None = None,
        name: str | None = None,
        workspace: str | None = None,
    ) -> "Sandbox":
        sandbox_id = uuid.uuid4()
        env_vars = env_vars or {}
        if not name:
            name = f"sbx-{sandbox_id.hex}"

        # TODO 表结构稳定后, 考虑再在表层面做约束?
        if (
            Sandbox.objects.filter(tenant_id=application.tenant_id, application=application, name=name)
            .exclude(status=SandboxStatus.DELETED.value)
            .exists()
        ):
            raise SandboxAlreadyExists(f"sandbox name {name} in application {application.code} already exists")

        # 分配可调度集群
        cluster = ClusterAllocator(
            AllocationContext(
                tenant_id=application.tenant_id,
                region=application.region,
                # Use agent_sandbox usage to allocate dedicated cluster for sandbox
                usage="agent_sandbox",
                # agent_sandbox 不区分环境
                environment="",
            )
        ).get_default()

        target = cluster.name
        # 随机选择 daemon_port，确保 (target, daemon_port) 唯一
        # TODO 表结构稳定后, 考虑在表层面做约束?
        used_ports = set(
            Sandbox.objects.filter(target=target)
            .exclude(status=SandboxStatus.DELETED.value)
            .values_list("daemon_port", flat=True)
        )
        # 单个集群, NodePort 类型的 service 的可用端口有范围限制
        daemon_port = find_available_port(
            settings.AGENT_SANDBOX_NODE_PORT_RANGE[0], settings.AGENT_SANDBOX_NODE_PORT_RANGE[1], used_ports
        )
        if daemon_port is None:
            raise SandboxCreateError(f"no available ports in cluster {target}")

        daemon_host = find_available_host(target)
        if not daemon_host:
            raise SandboxCreateError(f"no available nodes found in cluster {target}")

        return super().create(
            uuid=sandbox_id,
            application=application,
            name=name,
            snapshot=snapshot,
            snapshot_entrypoint=snapshot_entrypoint or [],
            workspace=workspace,
            target=target,
            env_vars=env_vars,
            status=SandboxStatus.PENDING.value,
            creator=creator,
            tenant_id=application.tenant_id,
            daemon_host=daemon_host,
            daemon_port=daemon_port,
            daemon_token=get_random_string(16),
        )


SandboxManager = models.Manager.from_queryset(SandboxQuerySet)


class Sandbox(UuidAuditedModel):
    """A sandbox is an isolated environment with filesystem and process management capabilities,
    typically used for running AI agent tasks.
    """

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="sandboxes")
    name = models.CharField(verbose_name="名称", max_length=64, help_text="租户内应用内唯一，未提供时自动生成")

    snapshot = models.CharField(verbose_name="快照名字", max_length=128, help_text="沙箱初始化使用的快照（镜像）")
    snapshot_entrypoint = models.JSONField(default=list, help_text="沙箱快照启动时指定的 entrypoint")
    workspace = models.CharField(verbose_name="工作空间", null=True, max_length=128, help_text="沙箱工作空间")

    target = models.CharField(verbose_name="目标区域", max_length=32, help_text="沙箱所属目标区域（集群）")
    env_vars = models.JSONField(verbose_name="环境变量", default=dict)
    cpu = models.DecimalField(verbose_name="CPU 上限（核）", max_digits=10, decimal_places=2, default="2")
    memory = models.DecimalField(verbose_name="内存上限（GB）", max_digits=10, decimal_places=2, default="1")

    daemon_host = models.CharField(max_length=128, help_text="daemon 服务的访问地址, 格式如 127.0.0.1")
    daemon_port = models.IntegerField(default=30000, help_text="daemon 服务的访问端口")
    daemon_token = EncryptField(help_text="daemon 服务的访问 token")

    status = models.CharField(verbose_name="状态", max_length=16, default=SandboxStatus.PENDING.value)

    started_at = models.DateTimeField("启动时间", null=True)
    deleted_at = models.DateTimeField("删除时间", null=True)

    creator = BkUserField()
    tenant_id = tenant_id_field_factory()

    objects = SandboxManager()

    @property
    def daemon_endpoint(self) -> str:
        return f"{self.daemon_host}:{self.daemon_port}"


def find_available_port(port_min: int, port_max: int, used_ports: set) -> int | None:
    """查找可用端口"""

    port_count = port_max - port_min + 1
    if len(used_ports) == port_count:
        # 端口已被耗尽
        return None

    # 利用"环形扫描"算法，从随机起点开始查找可用端口，避免展开整个端口范围
    # 随机选一个起始偏移量
    offset = random.randrange(port_count)
    daemon_port = next(
        (p for i in range(port_count) if (p := port_min + (offset + i) % port_count) not in used_ports),
        None,
    )
    return daemon_port


def find_available_host(cluster_name: str) -> str | None:
    # 从数据库获取集群最新的节点状态，提取节点 IP 列表
    cluster_state = RegionClusterState.objects.filter(cluster_name=cluster_name).order_by("-created").first()
    if not cluster_state:
        return None

    nodes_data = format_nodes_data(cluster_state.nodes_data)
    node_ips = [node["internal_ip_address"] for node in nodes_data if node.get("internal_ip_address")]

    if not node_ips:
        return None

    return random.choice(node_ips)
