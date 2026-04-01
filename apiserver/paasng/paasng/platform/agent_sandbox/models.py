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

import uuid

from blue_krill.models.fields import EncryptField
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import ClusterAllocator
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.agent_sandbox.image_build.constants import ImageBuildStatus
from paasng.platform.applications.models import Application
from paasng.utils.models import BkUserField, UuidAuditedModel

from .constants import SandboxStatus
from .exceptions import SandboxAlreadyExists


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
            AllocationContext.create_for_agent_sandbox(application.tenant_id, application.region)
        ).get_default()

        target = cluster.name

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


class ImageBuildRecord(UuidAuditedModel):
    """镜像构建记录，由第三方 sysapi client 发起，通过 Kaniko 等方式异步构建镜像。"""

    app_code = models.CharField(max_length=20, help_text="发起构建的应用 code，通常是 sysapi client 的 bk_app_code")
    source_url = models.CharField(max_length=1024, help_text="源码压缩包的 URL 地址")
    image_name = models.CharField(max_length=256, help_text="目标镜像名称")
    image_tag = models.CharField(max_length=128, help_text="目标镜像标签")
    dockerfile_path = models.CharField(max_length=512, default="Dockerfile", help_text="Dockerfile 相对路径")
    docker_build_args = models.JSONField(default=dict, blank=True, help_text="Docker 构建参数（--build-arg）")
    prepared_source_path = models.CharField(
        max_length=1024, default="", blank=True, help_text="预处理后上传到对象存储的源码包路径"
    )
    status = models.CharField(max_length=16, default=ImageBuildStatus.PENDING.value)
    started_at = models.DateTimeField(null=True, help_text="构建开始时间")
    completed_at = models.DateTimeField(null=True, help_text="构建完成时间")
    tenant_id = tenant_id_field_factory()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.uuid}-{self.image_name}:{self.image_tag}-{self.status}"

    def mark_as_building(self):
        """将构建状态标记为"构建中"并记录开始时间。"""
        self.status = ImageBuildStatus.BUILDING.value
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated"])

    def mark_as_completed(self, status: ImageBuildStatus, build_logs: str = ""):
        """将构建标记为终态（成功或失败），记录完成时间和日志。

        :param status: 终态，SUCCESSFUL 或 FAILED。
        :param build_logs: 构建日志，覆盖写入。
        """
        self.status = status.value
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated"])
        ImageBuildLog.objects.update_or_create(
            build=self,
            defaults={"content": build_logs, "tenant_id": self.tenant_id},
        )

    @property
    def output_image(self) -> str:
        """完整的镜像输出地址"""
        return f"{settings.AGENT_SANDBOX_DOCKER_REGISTRY_HOST}/{settings.AGENT_SANDBOX_DOCKER_REGISTRY_NAMESPACE}/{self.app_code}/{self.image_name}:{self.image_tag}"


class ImageBuildLog(UuidAuditedModel):
    """镜像构建日志，与 ImageBuildRecord 一对一关联"""

    build = models.OneToOneField(ImageBuildRecord, db_constraint=False, on_delete=models.CASCADE, related_name="log")
    content = models.TextField(default="", blank=True, help_text="构建容器的标准输出日志")
    tenant_id = tenant_id_field_factory()
