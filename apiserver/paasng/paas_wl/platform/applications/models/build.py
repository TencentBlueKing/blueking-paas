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
from typing import List, Optional

from django.db import models
from django.utils import timezone
from jsonfield import JSONCharField, JSONField

from paas_wl.platform.applications.constants import ArtifactType
from paas_wl.platform.applications.models import WlApp
from paas_wl.platform.applications.models.misc import OutputStream
from paas_wl.utils.constants import BuildStatus, make_enum_choices
from paas_wl.utils.models import UuidAuditedModel, validate_procfile
from paasng.dev_resources.sourcectl.models import VersionInfo


class Build(UuidAuditedModel):
    owner = models.CharField(max_length=64)
    app = models.ForeignKey('App', on_delete=models.CASCADE)

    # Slug path
    slug_path = models.TextField(help_text="slug path 形如 {region}/home/{name}:{branch}:{revision}/push", null=True)
    image = models.TextField(help_text="运行 Build 的镜像地址. 如果构件类型为 image，该值即构建产物", null=True)

    source_type = models.CharField(max_length=128, null=True)
    branch = models.CharField(max_length=128, null=True, help_text="readable version, such as trunk/master")
    revision = models.CharField(max_length=128, null=True, help_text="unique version, such as sha256")

    # Metadata
    procfile = JSONField(default={}, blank=True, validators=[validate_procfile])
    env_variables = JSONField(default=dict, blank=True)
    bkapp_revision_id = models.IntegerField(help_text="与本次构建关联的 BkApp Revision id", null=True)

    artifact_type = models.CharField(help_text="构件类型", default=ArtifactType.SLUG, max_length=16)
    artifact_deleted = models.BooleanField(default=False, help_text="slug/镜像是否已被清理")

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']

    @property
    def image_tag(self) -> Optional[str]:
        """从 image 字段分割出 tag 属性"""
        if not self.image:
            return None
        split = self.image.split(":", 1)
        if len(split) == 2:
            return split[1]
        # warning: no test cover
        # nobody know what kind of data will it be
        return split[0]

    def get_env_variables(self):
        """获取获取构建产物所需的环境变量"""
        if self.env_variables:
            return self.env_variables
        # NOTE: 理论上 envs 环境变量应该在创建 Build 时固化, 这里兼容了未增加 envs 字段前未生成 env_variables 的情况
        from paasng.engine.deploy.bg_build.utils import generate_launcher_env_vars

        self.env_variables = generate_launcher_env_vars(self.slug_path)
        self.save(update_fields=["env_variables", "updated"])
        return self.env_variables

    @property
    def version(self):
        return '%s:%s/%s' % (self.source_type, self.branch, self.revision)

    def __str__(self):
        return '%s-%s(%s)' % (self.uuid, self.app.name, self.app.region)


class BuildProcessManager(models.Manager):
    def new(
        self,
        owner: str,
        builder_image: str,
        source_tar_path: str,
        version_info: VersionInfo,
        invoke_message: str,
        buildpacks_info: Optional[List] = None,
    ):
        """Create a new release

        :param str owner: 发布者
        :param str builder_image: builder 镜像
        :param str source_tar_path: 源码上传到对象存储服务的路径
        :param VersionInfo version_info: 构建代码版本
        :param str invoke_message: 触发信息
        :param List buildpacks_info: 序列化后的 buildpacks 信息
        """

        # Get the largest(latest) version and increase it by 1.
        if not hasattr(self, "instance"):
            raise RuntimeError("Only call `new` method from RelatedManager.")

        if not isinstance(self.instance, WlApp):
            raise RuntimeError("Only call from app.build_set.")

        wl_app = self.instance
        latest_build = self.order_by('-generation').first()
        if latest_build:
            next_generation = latest_build.generation + 1
        else:
            next_generation = 1

        build_process = BuildProcess.objects.create(
            owner=owner,
            app=wl_app,
            image=builder_image,
            buildpacks=buildpacks_info or [],
            generation=next_generation,
            invoke_message=invoke_message,
            source_tar_path=source_tar_path,
            revision=version_info.revision,
            branch=version_info.version_name,
            output_stream=OutputStream.objects.create(),
        )
        return build_process


class BuildProcess(UuidAuditedModel):
    """This Build Process was invoked via a source tarball or anything similar"""

    owner = models.CharField(max_length=64)
    app = models.ForeignKey('App', null=True, on_delete=models.CASCADE)
    image = models.CharField(max_length=512, null=True, help_text="builder image")
    buildpacks = JSONCharField(max_length=4096, null=True)

    generation = models.PositiveBigIntegerField(verbose_name="自增ID", help_text="每个应用独立的自增ID")
    invoke_message = models.CharField(help_text="触发信息", max_length=255, null=True, blank=True)
    source_tar_path = models.CharField(max_length=2048)
    branch = models.CharField(max_length=128, null=True)
    revision = models.CharField(max_length=128, null=True)
    logs_was_ready_at = models.DateTimeField(null=True, help_text='Pod 状态就绪允许读取日志的时间')
    int_requested_at = models.DateTimeField(null=True, help_text='用户请求中断的时间')
    completed_at = models.DateTimeField(verbose_name="完成时间", help_text="failed/successful/interrupted 都是完成", null=True)

    status = models.CharField(choices=make_enum_choices(BuildStatus), max_length=12, default=BuildStatus.PENDING.value)
    output_stream = models.OneToOneField('OutputStream', null=True, on_delete=models.CASCADE)

    # A BuildProcess will result in a build and release, if succeeded
    build = models.OneToOneField('Build', null=True, related_name="build_process", on_delete=models.CASCADE)
    objects = BuildProcessManager()

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']

    def __str__(self):
        return '%s-%s(%s)-%s' % (self.uuid, self.app.name, self.app.region, self.status)

    def set_int_requested_at(self):
        """Set `int_requested_at` field"""
        self.int_requested_at = timezone.now()
        self.save(update_fields=['int_requested_at', 'completed_at', 'updated'])

    def check_interruption_allowed(self) -> bool:
        """Check if current build process allows interruptions"""
        if self.status in BuildStatus.get_finished_states():
            return False
        if not self.logs_was_ready_at:
            return False
        return True

    def set_logs_was_ready(self):
        """Mark current build was ready for reading logs from"""
        self.logs_was_ready_at = timezone.now()
        self.save(update_fields=['logs_was_ready_at', 'updated'])

    def update_status(self, status):
        """Update status and save"""
        self.status = status
        if status in [BuildStatus.FAILED, BuildStatus.SUCCESSFUL, BuildStatus.INTERRUPTED]:
            self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated'])

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
