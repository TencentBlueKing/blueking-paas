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
from django.db import models
from django.utils.crypto import get_random_string

from paas_wl.bk_app.agent_sandbox.cluster import find_available_port, list_available_hosts
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.applications.models import Application
from paasng.utils.models import BkUserField, UuidAuditedModel

from .constants import SandboxStatus
from .exceptions import SandboxAlreadyExists, SandboxCreateError


class SandboxManager(models.Manager):
    """沙箱 Manager 类"""

    def new(
        self,
        application: Application,
        creator: str,
        snapshot: str,
        snapshot_entrypoint: list | None = None,
        env_vars: dict | None = None,
        name: str | None = None,
        workspace: str | None = None,
    ):
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
        # 单个集群, NodePort 类型的 service 的可用端口限制在 30000~32767 之间
        daemon_port = find_available_port(30000, 32767, used_ports)
        if daemon_port is None:
            raise SandboxCreateError(f"no available ports in cluster {target}")

        available_hosts = list_available_hosts(target)
        if not available_hosts:
            raise SandboxCreateError(f"no available nodes found in cluster {target}")
        daemon_host = random.choice(available_hosts)

        return self.create(
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
            daemon_token=get_random_string(32),
        )


class Sandbox(UuidAuditedModel):
    """A sandbox is an isolated environment with filesystem and process management capabilities,
    typically used for running AI agent tasks.
    """

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="sandboxes"
    )
    name = models.CharField(verbose_name="名称", max_length=64, help_text="租户内应用内唯一，未提供时自动生成")

    snapshot = models.CharField(verbose_name="快照名字", max_length=128, help_text="沙箱初始化使用的快照（镜像）")
    # snapshot_entrypoint 是用户镜像(snapshot)的自定义入口启动命令(如 `start web`), 此时沙箱环境的启动命令变成 `/usr/local/bin/daemon start web`.
    # 对于 snapshot 而言, 它是 entrypoint, 对于 Pod 而言, 它是 args
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
    stopped_at = models.DateTimeField("停止时间", null=True)
    deleted_at = models.DateTimeField("删除时间", null=True)

    creator = BkUserField()
    tenant_id = tenant_id_field_factory()

    objects = SandboxManager()

    class Meta:
        unique_together = ("tenant_id", "application_id", "name")

    @property
    def daemon_endpoint(self) -> str:
        return f"{self.daemon_host}:{self.daemon_port}"
