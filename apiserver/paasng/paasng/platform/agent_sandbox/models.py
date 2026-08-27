# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from datetime import timedelta
from decimal import Decimal

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

from .constants import (
    DEFAULT_SANDBOX_CPU,
    DEFAULT_SANDBOX_MEMORY,
    SANDBOX_DEFAULT_TTL_SECONDS,
    SandboxStatus,
    SandboxWorkloadType,
)
from .e2b.constants import KEY_GENERATE_MAX_RETRIES, MAX_ACTIVE_KEYS_PER_APP
from .e2b.exceptions import E2BApiKeyGenerateError, E2BApiKeyQuotaExceeded
from .e2b.keys import generate_api_key, hash_api_key, make_display_prefix
from .exceptions import SandboxAlreadyExists, SandboxCreateError


class Volume(UuidAuditedModel):
    """共享存储卷，一个 Volume 对应 CFS 上 app/{uuid.hex} 子目录。"""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="agent_sandbox_volumes"
    )
    name = models.CharField(verbose_name="卷名称", max_length=256, help_text="应用内唯一标识")
    display_name = models.CharField(verbose_name="显示名称", max_length=256, blank=True, default="")
    deleted_at = models.DateTimeField("删除时间", null=True)
    tenant_id = tenant_id_field_factory()
    shared_app_codes = models.JSONField(
        verbose_name="共享给的应用 code 列表",
        default=list,
        help_text="被授权后可把该 Volume 挂到自己的沙箱；空列表表示不跨应用共享，最多 50 个",
    )

    class Meta:
        unique_together = ("tenant_id", "application_id", "name")

    @property
    def storage_path(self) -> str:
        """共享存储上的 subPath，格式为 app/{uuid_hex}。"""
        return f"app/{self.uuid.hex}"

    def allows_mount_by(self, application: Application) -> bool:
        """Whether ``application`` may mount this Volume into its sandbox."""
        if self.application_id == application.pk:
            return True
        return application.code in (self.shared_app_codes or [])


class VolumeArtifact(UuidAuditedModel):
    """Volume 内文件归档记录

    沙箱产物文件按需归档到 bkrepo(供前端直连下载/预览),该表记录 volume 内相对路径
    与 bkrepo 对象 key 的映射
    归档快判用 (mtime, size): 命中且一致则复用已归档对象
    """

    volume = models.ForeignKey(Volume, on_delete=models.CASCADE, db_constraint=False, related_name="artifacts")
    rel_path = models.CharField(verbose_name="volume 内相对路径", max_length=700)
    mtime = models.CharField(verbose_name="归档时文件 mtime", max_length=64, help_text="RFC3339，与 daemon 返回一致")
    size = models.BigIntegerField(verbose_name="归档时文件大小(字节)")
    sha256 = models.CharField(verbose_name="内容摘要", max_length=64)
    bkrepo_key = models.CharField(verbose_name="bkrepo 对象 key", max_length=1024)
    archived_at = models.DateTimeField(verbose_name="归档时间")
    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("volume", "rel_path")

    def is_fresh_for(self, mtime: str, size: int) -> bool:
        return self.mtime == mtime and self.size == size


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
        ttl_seconds: int = SANDBOX_DEFAULT_TTL_SECONDS,
        volume_mounts: list[dict] | None = None,
        cpu: Decimal | None = None,
        memory: Decimal | None = None,
        workload_type: str = SandboxWorkloadType.DEFAULT.value,
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

        # 分配可调度集群；SandboxInstance -> AGENT_SANDBOX_ISOLATED
        alloc_ctx = AllocationContext.create_for_agent_sandbox(
            application.tenant_id,
            application.region,
            is_isolated=workload_type == SandboxWorkloadType.SANDBOX_INSTANCE.value,
        )

        try:
            cluster = ClusterAllocator(alloc_ctx).get_default()
        except ValueError as exc:
            raise SandboxCreateError(f"no available cluster for workload_type={workload_type}: {exc}") from exc

        target = cluster.name

        # cpu / memory 未显式提供时, 走 Sandbox 模型字段默认值（平台默认规格）
        extra_resource_fields: dict = {}
        if cpu is not None:
            extra_resource_fields["cpu"] = cpu
        if memory is not None:
            extra_resource_fields["memory"] = memory

        return self.create(
            uuid=sandbox_id,
            application=application,
            name=name,
            snapshot=snapshot,
            snapshot_entrypoint=snapshot_entrypoint or [],
            workspace=workspace,
            target=target,
            env_vars=env_vars,
            volume_mounts=volume_mounts or [],
            workload_type=workload_type,
            status=SandboxStatus.PENDING.value,
            creator=creator,
            tenant_id=application.tenant_id,
            daemon_token=get_random_string(32),
            expired_at=timezone.now() + timedelta(seconds=ttl_seconds),
            **extra_resource_fields,
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
    volume_mounts = models.JSONField(
        verbose_name="挂载配置",
        default=list,
        help_text='已解析的共享卷挂载列表，格式 [{"volume_id": str, "mount_path": str}]',
    )
    cpu = models.DecimalField(
        verbose_name="CPU 上限（核）", max_digits=10, decimal_places=2, default=DEFAULT_SANDBOX_CPU
    )
    memory = models.DecimalField(
        verbose_name="内存上限（GB）", max_digits=10, decimal_places=2, default=DEFAULT_SANDBOX_MEMORY
    )
    # 创建时固定，生命周期内不支持切换
    workload_type = models.CharField(
        verbose_name="工作负载类型",
        max_length=16,
        default=SandboxWorkloadType.DEFAULT.value,
        help_text="沙箱运行时类型：default（普通 Pod）/ sandbox_instance",
    )

    daemon_token = EncryptField(help_text="daemon 服务的访问 token")

    status = models.CharField(verbose_name="状态", max_length=16, default=SandboxStatus.PENDING.value)

    started_at = models.DateTimeField("启动时间", null=True)
    stopped_at = models.DateTimeField("停止时间", null=True)
    deleted_at = models.DateTimeField("删除时间", null=True)
    expired_at = models.DateTimeField("过期时间(预计删除时间)", null=True, db_index=True)

    creator = BkUserField()
    tenant_id = tenant_id_field_factory()

    objects = SandboxManager()

    class Meta:
        unique_together = ("tenant_id", "application_id", "name")


class SandboxAppSettings(UuidAuditedModel):
    """沙箱的 app 级配置，各字段相互独立、按需填写，未填写的字段在创建沙箱时回退到平台默认值。

    当前已支持的配置项：
    - cpu / memory：沙箱资源上限，未配置时回退到 DEFAULT_SANDBOX_CPU / DEFAULT_SANDBOX_MEMORY。
    """

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="sandbox_app_settings",
    )
    cpu = models.DecimalField(verbose_name="CPU 上限（核）", max_digits=10, decimal_places=2, null=True, blank=True)
    memory = models.DecimalField(verbose_name="内存上限（GB）", max_digits=10, decimal_places=2, null=True, blank=True)
    tenant_id = tenant_id_field_factory()

    class Meta:
        verbose_name = "沙箱应用配置"


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


class E2BApiKeyManager(models.Manager):
    """E2BApiKey Manager 类"""

    def issue(self, application: Application, owner: str, name: str = "") -> tuple["E2BApiKey", str]:
        """签发一枚新 key。

        :param application: key 所属应用，也是后续 e2b 请求的归属主体
        :param owner: 签发人，用于审计
        :param name: 用户自定义的名称，便于在列表里区分多枚 key
        :return: (key 记录, 明文 key)。明文只在这一次返回，不入库
        :raises E2BApiKeyQuotaExceeded: 有效 key 数量已达上限
        :raises E2BApiKeyGenerateError: 连续多次生成的 key 都撞上了已有记录
        """
        active_count = self.filter(application=application, enabled=True).count()
        if active_count >= MAX_ACTIVE_KEYS_PER_APP:
            raise E2BApiKeyQuotaExceeded(
                f"application {application.code} already has {active_count} active e2b api keys"
            )

        for _ in range(KEY_GENERATE_MAX_RETRIES):
            plain_key = generate_api_key()
            key_hash = hash_api_key(plain_key)
            if self.filter(key_hash=key_hash).exists():
                continue
            api_key = self.create(
                application=application,
                name=name,
                key_hash=key_hash,
                key_prefix=make_display_prefix(plain_key),
                owner=owner,
                tenant_id=application.tenant_id,
            )
            return api_key, plain_key

        raise E2BApiKeyGenerateError(f"failed to generate a unique e2b api key after {KEY_GENERATE_MAX_RETRIES} tries")


class E2BApiKey(UuidAuditedModel):
    """apiserver 自行签发的 e2b API Key。

    标准 e2b SDK 只会在请求头里带 ``X-API-Key``，发不出 APIGW 所需的应用态凭证，
    所以 e2b 协议端点不能复用 ``IsAPIGWVerifiedApp``，需要这一套独立的凭证。

    底层沙箱集群 gateway 的真实凭证由 apiserver 独占持有，与本表没有任何映射关系：
    用户 key 泄露只影响该 key 名下的沙箱，不波及集群。
    """

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="e2b_api_keys"
    )
    name = models.CharField(verbose_name="名称", max_length=64, blank=True, default="", help_text="便于区分多枚 key")
    # 只存摘要，明文在签发响应里一次性返回后即不可再获取
    key_hash = models.CharField(verbose_name="密钥摘要", max_length=64, unique=True)
    key_prefix = models.CharField(verbose_name="密钥前缀", max_length=16, help_text="仅用于列表展示")
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    # 吊销采用置为失效而非物理删除，保留审计线索
    revoked_at = models.DateTimeField(verbose_name="吊销时间", null=True)

    owner = BkUserField(verbose_name="签发人")
    tenant_id = tenant_id_field_factory()

    objects = E2BApiKeyManager()

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["application", "enabled"])]

    def __str__(self):
        return f"{self.key_prefix}...({self.application_id})"

    def revoke(self):
        """吊销该 key，幂等。"""
        if not self.enabled:
            return
        self.enabled = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["enabled", "revoked_at", "updated"])
