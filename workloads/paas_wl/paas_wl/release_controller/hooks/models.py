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
import shlex
from typing import TYPE_CHECKING, Dict, List, Optional

from django.db import models
from django.utils import timezone

from paas_wl.platform.applications.models.app import App
from paas_wl.platform.applications.models.misc import OutputStream
from paas_wl.utils.constants import CommandStatus, CommandType
from paas_wl.utils.models import UuidAuditedModel

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.build import Build
    from paas_wl.platform.applications.models.config import Config


class CommandManager(models.Manager):
    def new(
        self,
        build: 'Build',
        type_: CommandType,
        command: str,
        operator: str,
        config: Optional['Config'] = None,
    ):
        """Create a new command for the build.

        :params build Build: 应用构建记录
        :params command str: hook 命名
        :params operator str: 操作者(被编码的 username), 目前该字段无意义
        :params config Optional[Config]: 应用配置, 包含环境变量和资源限制等信息. 如果不提供, 则获取上一个发布版本的应用配置
        """
        # TODO: 支持镜像部署后, 需要调整 build 参数的处理
        # Get the largest(latest) version and increase it by 1.
        if not hasattr(self, "instance"):
            raise RuntimeError("Only call `new` method from RelatedManager.")

        if not isinstance(self.instance, App):
            raise RuntimeError("Only call from app.command_set.")

        app = self.instance
        latest_obj = self.filter(type=type_.value).order_by('-version').first()
        if latest_obj:
            new_version = latest_obj.version + 1
            cfg = config or latest_obj.config
        else:
            new_version = 1
            cfg = config or app.config_set.latest()

        obj = self.create(
            type=type_.value,
            operator=operator,
            app=app,
            version=new_version,
            command=command,
            output_stream=OutputStream.objects.create(),
            build=build,
            config=cfg,
        )
        return obj


class Command(UuidAuditedModel):
    """The Command Model, which will be used to schedule a container running `command`,
    and store status, logs(and so on.) of the container."""

    type = models.CharField(choices=CommandType.get_choices(), max_length=32)

    app = models.ForeignKey('api.App', on_delete=models.CASCADE, db_constraint=False)
    version = models.PositiveIntegerField()
    command = models.TextField()
    exit_code = models.SmallIntegerField(null=True, help_text="容器结束状态码, -1 表示未知")
    status = models.CharField(choices=CommandStatus.get_choices(), max_length=12, default=CommandStatus.PENDING.value)
    logs_was_ready_at = models.DateTimeField(null=True, help_text='Pod 状态就绪允许读取日志的时间')
    int_requested_at = models.DateTimeField(null=True, help_text='用户请求中断的时间')
    output_stream = models.OneToOneField('api.OutputStream', null=True, on_delete=models.CASCADE)

    build = models.ForeignKey('api.Build', on_delete=models.CASCADE, null=True, db_constraint=False)
    config = models.ForeignKey('api.Config', on_delete=models.CASCADE, db_constraint=False)
    operator = models.CharField(max_length=64, help_text="操作者(被编码的 username), 目前该字段无意义")

    objects = CommandManager()

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']

    @property
    def region(self):
        return self.app.region

    @property
    def lines(self):
        return self.output_stream.lines.all().order_by('created')

    @property
    def split_command(self) -> List[str]:
        """Split command str to List"""
        return shlex.split(self.command)

    def get_envs(self) -> Dict:
        """获取与这个发布对象关联的环境变量"""
        envs = {}
        if self.build:
            envs.update(self.build.get_env_variables())
        envs.update(self.config.envs)
        return envs

    def update_status(self, status: CommandStatus, exit_code: Optional[int] = None):
        self.status = status.value
        if exit_code is not None:
            self.exit_code = exit_code
        self.save(update_fields=["status", "updated"])

    def set_logs_was_ready(self):
        """Mark current build was ready for reading logs from"""
        self.logs_was_ready_at = timezone.now()
        self.save(update_fields=['logs_was_ready_at', 'updated'])

    def set_int_requested_at(self):
        """Set `int_requested_at` field"""
        self.int_requested_at = timezone.now()
        self.save(update_fields=['int_requested_at', 'updated'])

    def check_interruption_allowed(self) -> bool:
        """Check if current command allows interruptions"""
        if CommandStatus(self.status) in CommandStatus.get_finished_states():
            return False
        if not self.logs_was_ready_at:
            return False
        return True
