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
from django.db import models
from django.utils import timezone
from jsonfield import JSONCharField, JSONField

from paas_wl.platform.applications.models import UuidAuditedModel
from paas_wl.utils.constants import BuildStatus, make_enum_choices
from paas_wl.utils.models import validate_procfile


class Build(UuidAuditedModel):
    owner = models.CharField(max_length=64)
    app = models.ForeignKey('App', on_delete=models.CASCADE)

    # Slug path
    slug_path = models.TextField(help_text="slug path 形如 {region}/home/{name}:{branch}:{revision}/push", null=True)
    image = models.TextField(
        help_text="镜像地址, 形如 {registry}/{platform_namespace}/{app_code}/{module}/{env}:{tag}", null=True
    )

    source_type = models.CharField(max_length=128, null=True)
    branch = models.CharField(max_length=128, null=True, help_text="readable version, such as trunk/master")
    revision = models.CharField(max_length=128, null=True, help_text="unique version, such as sha256")

    # Metadata
    procfile = JSONField(default={}, blank=True, validators=[validate_procfile])
    env_variables = JSONField(default=dict, blank=True)

    artifact_deleted = models.BooleanField(default=False, help_text="slug/镜像是否已被清理")

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']

    @property
    def type(self):
        return 'buildpack'

    @property
    def source_based(self):
        return True

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


class BuildProcess(UuidAuditedModel):
    """This Build Process was invoked via an source tarball or anything similar"""

    owner = models.CharField(max_length=64)
    app = models.ForeignKey('App', null=True, on_delete=models.CASCADE)
    image = models.CharField(max_length=512, null=True, help_text="builder image")
    buildpacks = JSONCharField(max_length=4096, null=True)

    source_tar_path = models.CharField(max_length=2048)
    branch = models.CharField(max_length=128, null=True)
    revision = models.CharField(max_length=128, null=True)
    logs_was_ready_at = models.DateTimeField(null=True, help_text='Pod 状态就绪允许读取日志的时间')
    int_requested_at = models.DateTimeField(null=True, help_text='用户请求中断的时间')

    status = models.CharField(choices=make_enum_choices(BuildStatus), max_length=12, default=BuildStatus.PENDING.value)
    output_stream = models.OneToOneField('OutputStream', null=True, on_delete=models.CASCADE)

    # A BuildProcess will result in a build and release, if succeeded
    build = models.OneToOneField('Build', null=True, related_name="build_process", on_delete=models.CASCADE)

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']

    def __str__(self):
        return '%s-%s(%s)-%s' % (self.uuid, self.app.name, self.app.region, self.status)

    def set_int_requested_at(self):
        """Set `int_requested_at` field"""
        self.int_requested_at = timezone.now()
        self.save(update_fields=['int_requested_at', 'updated'])

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
        self.save(update_fields=['status'])

    def success(self):
        """Shortcut for a BuildProcess Success"""
        self.update_status(status=BuildStatus.SUCCESSFUL.value)

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
