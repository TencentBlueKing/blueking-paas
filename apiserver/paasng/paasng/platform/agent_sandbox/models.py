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
from .e2b.constants import (
    KEY_GENERATE_MAX_RETRIES,
    MAX_ACTIVE_KEYS_PER_APP,
    RESOURCE_NAME_MAX_LENGTH,
    E2BSandboxStatus,
    E2BTemplateSyncStatus,
)
from .e2b.exceptions import (
    E2BApiKeyGenerateError,
    E2BApiKeyQuotaExceeded,
    E2BSandboxNotFound,
    E2BTemplateNotFound,
)
from .e2b.keys import generate_api_key, hash_api_key, make_display_prefix
from .exceptions import SandboxAlreadyExists, SandboxNoClusterError


class Volume(UuidAuditedModel):
    """共享存储卷，一个 Volume 对应 CFS 上 app/{uuid.hex} 子目录。"""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="agent_sandbox_volumes"
    )
    name = models.CharField(verbose_name="卷名称", max_length=256, help_text="应用内唯一标识")
    display_name = models.CharField(verbose_name="显示名称", max_length=256, blank=True, default="")
    deleted_at = models.DateTimeField("删除时间", null=True)
    # 进入删除流程的中间状态: 非空即表示该卷已不可再挂载, 但共享存储目录可能尚未清理完成.
    deleting_at = models.DateTimeField("开始删除时间", null=True)
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

    def count_active(self, application: Application) -> int:
        """统计应用下仍然占用集群资源的沙箱数量

        不计入:

        - 已软删除 (deleted_at 非空) 的沙箱: 其工作负载已不存在;
        - 创建失败 (err_creating) 的沙箱: 创建失败时已尝试清理其工作负载, 若该次清理本身失败,
          及仍不计入, 残留由过期沙箱清理命令在 TTL 到期后回收, 因此计数可能短暂偏低

        计入: 删除失败 (err_deleting) 的沙箱 -- 删除失败意味着工作负载可能仍然存在
        """
        return (
            self.filter(application=application, deleted_at__isnull=True)
            .exclude(status=SandboxStatus.ERR_CREATING.value)
            .count()
        )

    def new(
        self,
        application: Application,
        creator: str,
        *,
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
            raise SandboxNoClusterError(f"no available cluster for workload_type={workload_type}: {exc}") from exc

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
    - max_active_sandbox_count：应用可同时存活的沙箱数量上限，未配置时回退到 DEFAULT_MAX_ACTIVE_SANDBOX_COUNT。
    """

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="sandbox_app_settings",
    )
    cpu = models.DecimalField(verbose_name="CPU 上限（核）", max_digits=10, decimal_places=2, null=True, blank=True)
    memory = models.DecimalField(verbose_name="内存上限（GB）", max_digits=10, decimal_places=2, null=True, blank=True)
    max_active_sandbox_count = models.PositiveIntegerField(
        verbose_name="存活沙箱数量上限",
        null=True,
        blank=True,
        help_text="应用可同时存活的沙箱数量上限，未配置时回退到平台默认值",
    )
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


class E2BSandboxManager(models.Manager):
    """E2BSandbox Manager 类

    这里的两个查询方法是 e2b 沙箱的**唯一**归属判定入口，上层不得绕过它们
    自行拼 filter，更不得拿 gateway 的返回当归属依据。
    """

    def owned_by(self, application: Application) -> "models.QuerySet[E2BSandbox]":
        """列出该应用名下的沙箱"""
        return self.filter(application=application)

    def get_owned(self, application: Application, sandbox_id: str) -> "E2BSandbox":
        """取出属于该应用的沙箱。

        :raises E2BSandboxNotFound: 沙箱不存在，或存在但不属于该应用
        """
        try:
            return self.get(sandbox_id=sandbox_id, application=application)
        except E2BSandbox.DoesNotExist:
            # 两种情况共用一个异常，调用方据此一律返回 404：
            # 若区分开，攻击者就能用状态码探测某个沙箱 ID 是否存在
            raise E2BSandboxNotFound(f"sandbox {sandbox_id} not found")


class E2BSandbox(UuidAuditedModel):
    """e2b 沙箱的归属绑定。

    底层沙箱集群 gateway 没有租户概念，apiserver 用统一凭证访问时拿到的是全平台的沙箱全集。
    因此需要本表来绑定沙箱与应用的归属关系。
    """

    sandbox_id = models.CharField(
        verbose_name="沙箱 ID",
        # 按 claim 形态（e2b-envd-claim-...）留余量，不对格式做假设
        max_length=128,
        unique=True,
        help_text="gateway 返回的 ID",
    )
    # 归属主体
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, db_constraint=False, related_name="e2b_sandboxes"
    )
    cluster_name = models.CharField(verbose_name="所属集群", max_length=32)
    # 创建沙箱所用模板的资源名，即网关侧的模板标识。自定义模板的资源名带应用前缀，与 SDK 传入的不同
    template_id = models.CharField(verbose_name="模板标识", max_length=128, blank=True, default="")
    status = models.CharField(verbose_name="状态", max_length=16, default=E2BSandboxStatus.RUNNING.value)
    expired_at = models.DateTimeField(verbose_name="过期时间", null=True)

    tenant_id = tenant_id_field_factory()

    objects = E2BSandboxManager()

    class Meta:
        ordering = ["-created"]
        # 列表查询固定按「归属主体 + 状态」过滤，走这条联合索引避免全表扫描
        indexes = [models.Index(fields=["application", "status"])]

    def __str__(self):
        return f"{self.sandbox_id}({self.application_id})"


class E2BSandboxTemplateManager(models.Manager):
    """模板的可见性与可用性判定入口，上层不得绕过它们自行拼 filter。"""

    def builtins(self) -> "models.QuerySet[E2BSandboxTemplate]":
        return self.filter(application__isnull=True)

    def customs(self) -> "models.QuerySet[E2BSandboxTemplate]":
        """所有应用的自定义模板"""
        return self.filter(application__isnull=False)

    def custom_of(self, application: Application) -> "models.QuerySet[E2BSandboxTemplate]":
        return self.filter(application=application)

    def listable_by(self, application: Application) -> "models.QuerySet[E2BSandboxTemplate]":
        """应用在页面上能看到的模板：已启用且公开的内置模板，加上本应用的自定义模板"""
        return self.filter(
            models.Q(application__isnull=True, enabled=True, is_public=True) | models.Q(application=application)
        )

    def get_usable(self, application: Application, template_id: str) -> "E2BSandboxTemplate":
        """取出应用可以用来创建沙箱的模板。

        内置模板不看 is_public：不公开只影响页面展示，服务自用的模板要能通过 SDK 使用。
        自定义模板标识不会与内置模板重名，两个条件至多命中一个。

        :raises E2BTemplateNotFound: 模板不存在、已停用，或是其他应用的自定义模板
        """
        template = (
            self.filter(enabled=True, template_id=template_id)
            .filter(models.Q(application__isnull=True) | models.Q(application=application))
            .first()
        )
        if template is None:
            raise E2BTemplateNotFound(f"template {template_id} is not available")
        return template


class E2BSandboxTemplate(UuidAuditedModel):
    """e2b 沙箱模板，平台以它为准，向启用了 e2b 的集群下发同名的 SandboxTemplate 与 SandboxPool。

    - 内置模板：由平台管理员通过管理命令或平台管理页面维护，所有应用都可使用
    - 自定义模板：由应用自己创建，只有该应用可见、可用

    - enabled：SDK 只能用已启用的模板创建沙箱，停用不影响已下发的 CR
    - is_public：仅对内置模板生效，页面只展示公开的内置模板。不公开的模板（如某些服务自用的）
      仍可由知道 template_id 的调用方通过 SDK 使用，它不是访问控制

    [multi-tenancy] 内置模板全平台共享，不区分租户；自定义模板的 tenant_id 取所属应用的租户。
    """

    # 为空即内置模板。应用删除是软删除，自定义模板随之由清理流程删掉，不会因此变成内置模板
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        db_constraint=False,
        null=True,
        related_name="e2b_sandbox_templates",
    )
    template_id = models.CharField(verbose_name="模板标识", max_length=64, help_text="SDK 创建沙箱时传入的 templateID")
    # 内置模板与 template_id 相同，自定义模板为 {应用}--{template_id}。自定义模板的唯一性也由它保证
    resource_name = models.CharField(
        verbose_name="资源名",
        max_length=RESOURCE_NAME_MAX_LENGTH,
        unique=True,
        help_text="集群内 SandboxTemplate 与 SandboxPool 共用的名称，网关把它当作 e2b 的 templateID",
    )
    name = models.CharField(verbose_name="名称", max_length=64)
    description = models.TextField(verbose_name="描述", blank=True, default="")
    image = models.CharField(verbose_name="镜像", max_length=256)
    cpu_count = models.PositiveIntegerField(verbose_name="CPU 核数")
    memory_mb = models.PositiveIntegerField(verbose_name="内存（MB）")
    disk_size_mb = models.PositiveIntegerField(
        verbose_name="系统盘（MB）",
        null=True,
        help_text="为空时不挂载独立系统盘，使用运行时默认的根文件系统；填写时为每个沙箱创建一块该大小的 PVC 作为系统盘",
    )
    env_vars = models.JSONField(verbose_name="环境变量", default=dict, blank=True)
    workdir = models.CharField(verbose_name="工作目录", max_length=256, blank=True, default="")
    # 自定义模板固定为 0，靠网关在无库存时现场创建
    prewarm_count = models.PositiveIntegerField(verbose_name="预热数量", default=0)
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    # 默认不公开：漏配时只是页面上看不到，不会把内部模板误展示出去
    is_public = models.BooleanField(verbose_name="是否公开", default=False, help_text="是否在开发者中心页面展示")

    tenant_id = tenant_id_field_factory()

    objects = E2BSandboxTemplateManager()

    class Meta:
        ordering = ["template_id"]

    def __str__(self):
        return self.resource_name

    @property
    def is_builtin(self) -> bool:
        return self.application_id is None


class E2BSandboxTemplateSyncRecord(UuidAuditedModel):
    """模板在单个集群上的下发状态。

    每个目标集群恰好一条：保存模板时即为所有目标集群写入待同步，不再是目标的集群的记录随之删除，
    因此记录齐全即可据此判断模板或集群是否同步完成。

    status 是最近一次下发的进度，只供运维排查；集群里是不是当前配置看 applied_digest，
    能否用模板创建沙箱以它为准。

    [multi-tenancy] This model is not tenant-aware.
    """

    template = models.ForeignKey(
        E2BSandboxTemplate, on_delete=models.CASCADE, db_constraint=False, related_name="sync_records"
    )
    cluster_name = models.CharField(verbose_name="集群名称", max_length=64)
    status = models.CharField(
        verbose_name="同步状态", max_length=16, choices=E2BTemplateSyncStatus.get_django_choices()
    )
    message = models.TextField(verbose_name="失败原因", blank=True, default="")
    # 置为待同步、下发失败时不动：集群里还是上次下发成功的配置
    applied_digest = models.CharField(
        verbose_name="已下发的配置摘要", max_length=64, blank=True, default="", help_text="为空表示从未下发成功"
    )

    class Meta:
        unique_together = ("template", "cluster_name")
        ordering = ["cluster_name"]
