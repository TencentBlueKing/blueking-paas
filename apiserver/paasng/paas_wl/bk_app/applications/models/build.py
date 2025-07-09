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

import logging
import os
import shlex
from typing import Dict, List, Optional

from blue_krill.storages.blobstore.base import SignatureType
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from jsonfield import JSONCharField, JSONField
from moby_distribution.registry.client import APIEndpoint, DockerRegistryV2Client
from moby_distribution.registry.exceptions import PermissionDeny, ResourceNotFound, UnSupportMediaType
from moby_distribution.registry.resources.manifests import ManifestRef, ManifestSchema2
from moby_distribution.registry.utils import parse_image

from paas_wl.bk_app.applications.constants import ArtifactType
from paas_wl.bk_app.applications.entities import BuildArtifactMetadata
from paas_wl.bk_app.applications.models.misc import OutputStream
from paas_wl.infras.cluster.utils import get_image_registry_by_app
from paas_wl.utils.blobstore import make_blob_store
from paas_wl.utils.constants import BuildStatus
from paas_wl.utils.models import UuidAuditedModel, make_json_field
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.sourcectl.models import VersionInfo

# Slug runner 默认的 entrypoint, 平台所有 slug runner 镜像都以该值作为入口
# TODO: 需验证存量所有镜像是否都设置了默认的 entrypoint, 如是, 即可移除所有 DEFAULT_SLUG_RUNNER_ENTRYPOINT
DEFAULT_SLUG_RUNNER_ENTRYPOINT = ["bash", "/runner/init"]

# CNB runner 默认的 entrypoint
# see: https://buildpacks.io/docs/for-platform-operators/concepts/lifecycle/launch/
DEFAULT_CNB_RUNNER_ENTRYPOINT = ["launcher"]

logger = logging.getLogger(__name__)

BuildArtifactMetadataField = make_json_field("BuildArtifactMetadataField", py_model=BuildArtifactMetadata)


class Build(UuidAuditedModel):
    application_id = models.UUIDField(verbose_name="所属应用", null=True)
    module_id = models.UUIDField(verbose_name="所属模块", null=True)

    owner = models.CharField(max_length=64)
    app = models.ForeignKey("App", null=True, on_delete=models.CASCADE, help_text="[deprecated] wl_app 外键")

    # Slug path
    slug_path = models.TextField(help_text="slug path 形如 {region}/home/{name}:{branch}:{revision}/push", null=True)
    image = models.TextField(
        help_text="运行 Build 的镜像地址. 如果构件类型为 image，该值即构建产物; 如果构建产物是 Slug, 则返回 SlugRunner 的镜像",
        null=True,
    )

    # 源码信息
    source_type = models.CharField(max_length=128, null=True)
    branch = models.CharField(max_length=128, null=True, help_text="readable version, such as trunk/master")
    revision = models.CharField(max_length=128, null=True, help_text="unique version, such as sha256")

    env_variables = JSONField(default=dict, blank=True)
    bkapp_revision_id = models.IntegerField(help_text="与本次构建关联的 BkApp Revision id", null=True)

    artifact_type = models.CharField(help_text="构件类型", default=ArtifactType.SLUG, max_length=16)
    artifact_detail = models.JSONField(default={}, help_text="构件详情(展示信息)")
    artifact_deleted = models.BooleanField(default=False, help_text="slug/镜像是否已被清理")

    artifact_metadata = BuildArtifactMetadataField(
        default=BuildArtifactMetadata,
        help_text="构件元信息, 包括 entrypoint/use_cnb/use_dockerfile/proc_entrypoints 等信息",
    )

    tenant_id = tenant_id_field_factory()

    class Meta:
        get_latest_by = "created"
        ordering = ["-created"]

    def get_image(self) -> str:
        """运行 Build 的镜像地址"""
        if self.image:
            return self.image
        # 兜底逻辑, 兼容未绑定运行时的迁移应用或历史数据
        return self.app.latest_config.get_image()

    def is_build_from_cnb(self) -> bool:
        """获取当前 Build 构件是否基于 cnb 构建"""
        return bool(self.artifact_metadata.use_cnb)

    def get_universal_entrypoint(self) -> List[str]:
        """获取使用 Build 运行 hook 等命令的 entrypoint"""
        if self.is_build_from_cnb():
            # cnb 运行时执行其他命令需要用 `launcher` 进入 buildpack 上下文
            # See: https://github.com/buildpacks/lifecycle/blob/main/cmd/launcher/cli/launcher.go
            return DEFAULT_CNB_RUNNER_ENTRYPOINT

        if self.artifact_type == ArtifactType.SLUG:
            return self.artifact_metadata.entrypoint or DEFAULT_SLUG_RUNNER_ENTRYPOINT

        # 旧镜像应用分支
        # Note: 关于为什么要使用 env 命令作为 entrypoint, 而不是直接将用户的命令作为 entrypoint.
        # 虽然实际上绝大部分 CRI 实现会在当 Command 非空时 忽略镜像的 CMD(即认为 ENTRYPOINT 和 CMD 是绑定的, 只要 ENTRYPOINT 被修改, 就会忽略 CMD)
        # 但是, 根据 k8s 的文档, 如果 Command/Args 是空值，就会使用镜像的 ENTRYPOINT 和 CMD.
        # 而 Heroku 风格的 Procfile 不是以 entrypoint/cmd 这样的格式描述, 如果只将 procfile 作为 Container 的 Command/Args 都会有潜在风险.
        # 风险点在于: Command/Args 为空时, 有可能会使用镜像的 ENTRYPOINT 和 CMD.
        # ref: https://github.com/containerd/containerd/blob/main/pkg/cri/opts/spec_opts.go#L63
        return ["env"]

    def get_entrypoint_for_proc(self, process_type: str) -> List[str]:
        """获取使用 Build 运行 process_type 的 entrypoint"""
        if (proc_entrypoints := self.artifact_metadata.proc_entrypoints) and (
            entrypoint := proc_entrypoints.get(process_type)
        ):
            return entrypoint

        return self._get_default_entrypoint(process_type)

    def get_command_for_proc(self, process_type: str, proc_command: str) -> List[str]:
        """获取运行 Build 的 command"""
        if self.is_build_from_cnb():
            # cnb 运行时的 command 是空列表
            # See: https://github.com/buildpacks/lifecycle/blob/main/cmd/launcher/cli/launcher.go#L78
            return []

        if self.artifact_type == ArtifactType.SLUG:
            return ["start", process_type]

        return shlex.split(proc_command)

    def _get_default_entrypoint(self, process_type: str) -> List[str]:
        if self.is_build_from_cnb():
            # cnb 运行时的 entrypoint 是 process_type
            # See: https://github.com/buildpacks/lifecycle/blob/main/cmd/launcher/cli/launcher.go#L78
            return [process_type]

        return self.get_universal_entrypoint()

    @property
    def image_repository(self) -> Optional[str]:
        """从 image 字段分割出 repository 属性"""
        if not self.image:
            return None
        repository, _, tag = self.image.partition(":")
        return repository

    @property
    def image_tag(self) -> Optional[str]:
        """从 image 字段分割出 tag 属性"""
        if not self.image:
            return None
        repository, _, tag = self.image.partition(":")
        if tag:
            return tag
        # warning: no test cover
        # nobody know what kind of data will it be
        return repository

    def get_env_variables(self):
        """获取获取构建产物所需的环境变量"""
        if self.env_variables:
            return self.env_variables
        # NOTE: 理论上 envs 环境变量应该在创建 Build 时固化, 这里兼容了未增加 envs 字段前未生成 env_variables 的情况
        self.env_variables = _generate_launcher_env_vars(self.slug_path)
        self.save(update_fields=["env_variables", "updated"])
        return self.env_variables

    def get_artifact_detail(self):
        """获取构件详情, 如果构件详情未初始化, 则进行初始化"""
        if self.artifact_detail:
            return self.artifact_detail

        self.artifact_detail = {"invoke_message": self.build_process.invoke_message}

        if self.artifact_type == ArtifactType.IMAGE:
            image_registry = get_image_registry_by_app(self.app)
            registry_client = DockerRegistryV2Client.from_api_endpoint(
                api_endpoint=APIEndpoint(url=image_registry.host),
                username=image_registry.username,
                password=image_registry.password,
            )
            image = parse_image(self.image, default_registry=image_registry.host)
            ref = ManifestRef(repo=image.name, reference=image.tag, client=registry_client)

            metadata = None
            try:
                metadata = ref.get_metadata()
            except (PermissionDeny, ResourceNotFound, UnSupportMediaType) as e:
                # 由于集群关联的镜像仓库可能被修改，导致历史的构建所关联的镜像不一定能查询到，这里需要忽略
                logger.warning(f"Failed to get metadata of image {self.image}: {e}")

            size, digest = 0, "unknown"
            if metadata:
                manifest: ManifestSchema2 = ref.get()
                size = sum(layer.size for layer in manifest.layers)
                digest = metadata.digest

            self.artifact_detail.update({"size": size, "digest": digest})

        self.save(update_fields=["artifact_detail", "updated"])
        return self.artifact_detail

    def artifact_invoke_message(self):
        """获取构建详情，需要单独做国际化处理"""
        if self.artifact_detail:
            return _(self.artifact_detail["invoke_message"])
        return _(self.build_process.invoke_message)

    @property
    def version(self):
        return "%s:%s/%s" % (self.source_type, self.branch, self.revision)

    def __str__(self):
        return "%s-%s(%s)" % (self.uuid, self.app.name, self.app.region)


class BuildProcessManager(models.Manager):
    def new(
        self,
        env: ModuleEnvironment,
        builder_image: str,
        source_tar_path: str,
        version_info: VersionInfo,
        invoke_message: str,
        owner: str,
        buildpacks_info: Optional[List] = None,
    ):
        """Create a new build processes

        :param str env: 执行本次构建的环境
        :param str owner: 发布者
        :param str builder_image: builder 镜像
        :param str source_tar_path: 源码上传到对象存储服务的路径
        :param VersionInfo version_info: 构建代码版本
        :param str invoke_message: 触发信息
        :param List buildpacks_info: 序列化后的 buildpacks 信息
        """

        # Get the largest(latest) version and increase it by 1.
        if hasattr(self, "instance"):
            raise RuntimeError("Can not call `new` method from RelatedManager.")

        application_id = env.application_id
        module_id = env.module_id
        wl_app = env.wl_app
        latest_bp = self.filter(module_id=module_id).order_by("-generation").first()  # type: BuildProcess
        if latest_bp:
            next_generation = latest_bp.generation + 1

        else:
            next_generation = 1

        build_process = BuildProcess.objects.create(
            owner=owner,
            application_id=application_id,
            module_id=module_id,
            app=wl_app,
            image=builder_image,
            buildpacks=buildpacks_info or [],
            generation=next_generation,
            invoke_message=invoke_message,
            source_tar_path=source_tar_path,
            revision=version_info.revision,
            branch=version_info.version_name,
            output_stream=OutputStream.objects.create(),
            tenant_id=wl_app.tenant_id,
        )
        return build_process


class BuildProcess(UuidAuditedModel):
    """This Build Process was invoked via a source tarball or anything similar"""

    application_id = models.UUIDField(verbose_name="所属应用", null=True)
    module_id = models.UUIDField(verbose_name="所属模块", null=True)

    owner = models.CharField(max_length=64)
    app = models.ForeignKey("App", null=True, on_delete=models.CASCADE, help_text="[deprecated] wl_app 外键")
    image = models.CharField(max_length=512, null=True, help_text="builder image")
    buildpacks = JSONCharField(max_length=4096, null=True)

    generation = models.PositiveBigIntegerField(verbose_name="自增ID", help_text="每个应用独立的自增ID")
    invoke_message = models.CharField(help_text="触发信息", max_length=255, null=True, blank=True)
    source_tar_path = models.CharField(max_length=2048)
    branch = models.CharField(max_length=128, null=True)
    revision = models.CharField(max_length=128, null=True)
    logs_was_ready_at = models.DateTimeField(null=True, help_text="Pod 状态就绪允许读取日志的时间")
    int_requested_at = models.DateTimeField(null=True, help_text="用户请求中断的时间")
    completed_at = models.DateTimeField(
        verbose_name="完成时间", help_text="failed/successful/interrupted 都是完成", null=True
    )

    status = models.CharField(max_length=12, default=BuildStatus.PENDING.value)
    output_stream = models.OneToOneField("OutputStream", null=True, on_delete=models.CASCADE)

    # A BuildProcess will result in a build and release, if succeeded
    build = models.OneToOneField("Build", null=True, related_name="build_process", on_delete=models.CASCADE)

    tenant_id = tenant_id_field_factory()

    objects = BuildProcessManager()

    class Meta:
        get_latest_by = "created"
        ordering = ["-created"]

    def __str__(self):
        return "%s-%s(%s)-%s" % (self.uuid, self.app.name, self.app.region, self.status)

    def is_finished(self):
        return self.status in BuildStatus.get_finished_states()

    def set_int_requested_at(self):
        """Set `int_requested_at` field"""
        self.int_requested_at = timezone.now()
        self.save(update_fields=["int_requested_at", "completed_at", "updated"])

    def check_interruption_allowed(self) -> bool:
        """Check if current build process allows interruptions"""
        if self.is_finished():
            return False

        return self.logs_was_ready_at is not None

    def set_logs_was_ready(self):
        """Mark current build was ready for reading logs from"""
        self.logs_was_ready_at = timezone.now()
        self.save(update_fields=["logs_was_ready_at", "updated"])

    def update_status(self, status):
        """Update status and save"""
        self.status = status
        if status in [BuildStatus.FAILED, BuildStatus.SUCCESSFUL, BuildStatus.INTERRUPTED]:
            self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated"])

    def buildpacks_as_build_env(self) -> str:
        """buildpacks to slugbuilder REQUIRED_BUILDPACKS env"""
        buildpacks = self.buildpacks
        if not buildpacks:
            return ""

        required_buildpacks = []
        for i in buildpacks:
            buildpack = []
            for key in ("type", "name", "url", "version"):
                buildpack.append(i.get(key) or '""')

            required_buildpacks.append(" ".join(buildpack))

        return ";".join(required_buildpacks)


def _generate_launcher_env_vars(slug_path: str) -> Dict[str, str]:
    # This function is a duplication of paasng.platform.engine.deploy.bg_build.utils to void dep problem
    store = make_blob_store(bucket=settings.BLOBSTORE_BUCKET_APP_SOURCE)
    object_key = os.path.join(slug_path, "slug.tgz")
    return {
        "SLUG_URL": os.path.join(settings.BLOBSTORE_BUCKET_APP_SOURCE, object_key),
        # 以下是新的环境变量, 通过签发 http 协议的变量屏蔽对象存储仓库的实现.
        "SLUG_GET_URL": store.generate_presigned_url(
            # slug get url 签发尽可能长的时间, 避免应用长期不部署, 重新调度后无法运行。
            key=object_key,
            expires_in=60 * 60 * 24 * 365 * 20,
            signature_type=SignatureType.DOWNLOAD,
        ),
    }
