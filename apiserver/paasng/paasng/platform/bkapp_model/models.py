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
from functools import lru_cache
from typing import List, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from paas_wl.utils.models import TimestampedModel
from paasng.platform.engine.constants import AppEnvName, ImagePullPolicy
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models import Module


def env_overlay_getter_factory(field_name: str):
    """a proxy to get env overlay field"""

    @lru_cache
    def func(self: "ModuleProcessSpec", environment_name: str):
        try:
            return getattr(self.env_overlays.get(environment_name=environment_name), field_name)
        except ObjectDoesNotExist:
            return getattr(self, field_name)

    return func


class ModuleProcessSpec(TimestampedModel):
    """模块维度的进程定义, 表示模块当前所定义的进程, 该模型只通过 API 变更

    部署应用时会同步到 paas_wl.ProcessSpec, 需保证字段与 ProcessSpec 一致"""

    module = models.ForeignKey(
        'modules.Module', on_delete=models.CASCADE, db_constraint=False, related_name="process_specs"
    )
    name = models.CharField('进程名称', max_length=32)

    proc_command = models.TextField(help_text="进程启动命令(包含完整命令和参数的字符串), 只能与 command/args 二选一", null=True)
    command: Optional[List[str]] = models.JSONField(help_text="容器执行命令", default=None, null=True)
    args: Optional[List[str]] = models.JSONField(help_text="命令参数", default=None, null=True)
    port = models.IntegerField(help_text="容器端口", null=True)

    # Deprecated: 仅用于 v1alpha1 的云原生应用
    image = models.CharField(help_text="容器镜像, 仅用于 v1alpha1 的云原生应用", max_length=255, null=True)
    image_pull_policy = models.CharField(
        help_text="镜像拉取策略(仅用于 v1alpha1 的云原生应用)",
        choices=ImagePullPolicy.get_choices(),
        default=ImagePullPolicy.IF_NOT_PRESENT,
        max_length=20,
    )
    image_credential_name = models.CharField(help_text="镜像拉取凭证名(仅用于 v1alpha1 的云原生应用)", max_length=64, null=True)

    # Global settings
    target_replicas = models.IntegerField('期望副本数', default=1)
    plan_name = models.CharField(help_text="仅存储方案名称", max_length=32)
    autoscaling = models.BooleanField('是否启用自动扩缩容', default=False)
    scaling_config = models.JSONField('自动扩缩容配置', null=True)

    class Meta:
        unique_together = ("module", "name")

    def get_proc_command(self) -> str:
        if self.proc_command:
            return self.proc_command
        return shlex.join(self.command or []) + " " + shlex.join(self.args or [])

    get_target_replicas = env_overlay_getter_factory("target_replicas")
    get_plan_name = env_overlay_getter_factory("plan_name")
    get_autoscaling = env_overlay_getter_factory("autoscaling")
    get_scaling_config = env_overlay_getter_factory("scaling_config")


class ProcessSpecEnvOverlay(TimestampedModel):
    """进程定义中允许按环境覆盖的配置"""

    proc_spec = models.ForeignKey(
        ModuleProcessSpec, on_delete=models.CASCADE, db_constraint=False, related_name="env_overlays"
    )
    environment_name = models.CharField(
        verbose_name=_('环境名称'), choices=AppEnvName.get_choices(), null=False, max_length=16
    )

    target_replicas = models.IntegerField('期望副本数', default=1)
    plan_name = models.CharField(help_text="仅存储方案名称", max_length=32)
    autoscaling = models.BooleanField('是否启用自动扩缩容', default=False)
    scaling_config = models.JSONField('自动扩缩容配置', null=True)

    class Meta:
        unique_together = ("proc_spec", "environment_name")


class ModuleDeployHookManager(models.Manager):
    def _get_caller(self) -> Module:
        if not hasattr(self, "instance"):
            raise RuntimeError("Only call `upsert` method from RelatedManager.")

        if not isinstance(self.instance, Module):
            raise RuntimeError("Only call from module.deploy_hooks")
        return self.instance

    def upsert(
        self,
        type_: DeployHookType,
        proc_command: Optional[str] = None,
        command: Optional[List[str]] = None,
        args: Optional[List[str]] = None,
    ) -> 'ModuleDeployHook':
        """upsert a ModuleDeployHook with args, will auto enable it if it is disabled"""
        module = self._get_caller()
        if proc_command is not None:
            hook, _ = self.update_or_create(
                module=module, type=type_, defaults={"proc_command": proc_command, "enabled": True}
            )
        elif command is not None and args is not None:
            hook, _ = self.update_or_create(
                module=module, type=type_, defaults={"command": command, "args": args, "enabled": True}
            )
        else:
            raise ValueError("invalid value to upsert ModuleDeployHook")
        return hook

    def disable(self, type_: DeployHookType):
        """disable a ModuleDeployHook by type"""
        module = self._get_caller()
        hook, _ = self.update_or_create(module=module, type=type_, defaults={"enabled": False})
        return hook

    def get_by_type(self, type_: DeployHookType) -> Optional['ModuleDeployHook']:
        """get hook by type, return None if not found"""
        module = self._get_caller()
        try:
            return self.get(module=module, type=type_)
        except ObjectDoesNotExist:
            return None


class ModuleDeployHook(TimestampedModel):
    """钩子命令"""

    module = models.ForeignKey(
        'modules.Module', on_delete=models.CASCADE, db_constraint=False, related_name="deploy_hooks"
    )
    type = models.CharField(help_text="钩子类型", max_length=20, choices=DeployHookType.get_choices())

    proc_command = models.TextField(help_text="进程启动命令(包含完整命令和参数的字符串), 只能与 command/args 二选一", null=True)
    command: Optional[List[str]] = models.JSONField(help_text="容器执行命令", default=None, null=True)
    args: Optional[List[str]] = models.JSONField(help_text="命令参数", default=None, null=True)
    enabled = models.BooleanField(help_text="是否已开启", default=False)

    objects = ModuleDeployHookManager()

    class Meta:
        unique_together = ("module", "type")

    def get_proc_command(self) -> str:
        if self.proc_command is not None:
            return self.proc_command
        return shlex.join(self.command or []) + " " + shlex.join(self.args or [])
