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

import shlex
from typing import TYPE_CHECKING, Dict, List, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from paas_wl.utils.models import AuditedModel, TimestampedModel
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.bkapp_model.entities import (
    AutoscalingConfig,
    Component,
    HostAlias,
    Metric,
    Monitoring,
    ProbeSet,
    ProcService,
    SvcDiscEntryBkSaaS,
)
from paasng.platform.declarative.deployment.svc_disc import BkSaaSEnvVariableFactory
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.models import Module
from paasng.utils.models import make_json_field

if TYPE_CHECKING:
    from typing import Callable  # noqa: F401


def env_overlay_getter_factory(field_name: str):
    """a proxy to get env overlay field"""

    def func(self: "ModuleProcessSpec", environment_name: str):
        try:
            val = getattr(self.env_overlays.get(environment_name=environment_name), field_name)
        except ObjectDoesNotExist:
            return getattr(self, field_name)

        # When the value defined in the overlay object is None, which means the value
        # is absent, ignore it and return the value defined in the base module object.
        if val is None:
            return getattr(self, field_name)
        return val

    return func


AutoscalingConfigField = make_json_field("AutoscalingConfigField", AutoscalingConfig)
ProbeSetField = make_json_field("ProbeSetField", ProbeSet)
ProcServicesField = make_json_field("ProcServicesField", List[ProcService])
ComponentsField = make_json_field("ComponentsField", List[Component])


class ModuleProcessSpec(TimestampedModel):
    """模块维度的进程定义, 表示模块当前所定义的进程, 该模型只通过 API 变更

    部署应用时会同步到 paas_wl.ProcessSpec, 需保证字段与 ProcessSpec 一致"""

    module = models.ForeignKey(
        "modules.Module", on_delete=models.CASCADE, db_constraint=False, related_name="process_specs"
    )
    name = models.CharField("进程名称", max_length=32)

    proc_command = models.TextField(
        help_text="进程启动命令(包含完整命令和参数的字符串), 只能与 command/args 二选一", null=True
    )
    command: Optional[List[str]] = models.JSONField(help_text="容器执行命令", default=None, null=True)
    args: Optional[List[str]] = models.JSONField(help_text="命令参数", default=None, null=True)
    port = models.IntegerField(help_text="[deprecated] 容器端口", null=True)
    services: Optional[List[ProcService]] = ProcServicesField(help_text="进程服务列表", default=None, null=True)

    # Global settings
    target_replicas = models.IntegerField("期望副本数", default=1)
    plan_name = models.CharField(help_text="仅存储方案名称", max_length=32)
    autoscaling = models.BooleanField("是否启用自动扩缩容", default=False)
    scaling_config: Optional[AutoscalingConfig] = AutoscalingConfigField("自动扩缩容配置", null=True)
    probes: Optional[ProbeSet] = ProbeSetField("容器探针配置", default=None, null=True)
    components: Optional[List[Component]] = ComponentsField("组件配置", default=None, null=True)

    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("module", "name")
        ordering = ["id"]

    def get_proc_command(self) -> str:
        """获取 Procfile 形式的命令
        使用场景:
        - views 数据展示
        - 旧镜像应用启动进程(旧镜像应用进程直接返回 proc_command)
        """
        if self.proc_command:
            return self.proc_command
        # FIXME: proc_command 并不能简单地通过 shlex.join 合并 command 和 args 生成
        # 已知 shlex.join 不支持环境变量, 如果普通应用使用 app_desc v3 描述文件, 有可能出现无法正常运行的问题
        # 例如会报错: Error: '${PORT:-5000}' is not a valid port number.
        # 如果实际用于命令执行, 可参考 generate_bash_command_with_tokens 函数实现
        return self._sanitize_proc_command(
            (shlex.join(self.command or []) + " " + shlex.join(self.args or [])).strip()
        )

    @staticmethod
    def _sanitize_proc_command(proc_command: str) -> str:
        """Sanitize the command and arg list, replace some special expressions which can't
        be interpreted by the operator.
        """
        # '${PORT:-5000}' is massively used by the app framework, while it can not work well with shlex.join,
        # here remove the single quote added by shlex.join.
        known_cases = [
            ("':$PORT'", ":$PORT"),
            ("':${PORT:-5000}'", ":${PORT}"),
            ("'[::]:${PORT}'", "[::]:${PORT}"),
            ("'[::]:${PORT:-5000}'", "[::]:${PORT}"),
        ]
        for old, new in known_cases:
            proc_command = proc_command.replace(old, new)
        return proc_command

    get_target_replicas = env_overlay_getter_factory("target_replicas")  # type: Callable[[str], int]
    get_plan_name = env_overlay_getter_factory("plan_name")  # type: Callable[[str], str]
    get_autoscaling = env_overlay_getter_factory("autoscaling")  # type: Callable[[str], bool]
    get_scaling_config = env_overlay_getter_factory("scaling_config")  # type: Callable[[str], Optional[AutoscalingConfig]]


class ProcessSpecEnvOverlayManager(models.Manager):
    """Custom manager for ProcessSpecEnvOverlay"""

    def save_by_module(
        self,
        module: Module,
        proc_name: str,
        env_name: str,
        plan_name: Optional[str] = None,
        target_replicas: Optional[int] = None,
        autoscaling: bool = False,
        scaling_config: Optional[Dict] = None,
    ):
        """Save an overlay data by module and process name.

        :param module: module instance
        :param proc_name: process name
        :param env_name: environment name
        """
        proc_spec = ModuleProcessSpec.objects.get(module=module, name=proc_name)
        if scaling_config:
            # Use AutoscalingConfig to validate the input
            scaling_config_dict = AutoscalingConfig(**scaling_config).dict()
        else:
            scaling_config_dict = None

        ProcessSpecEnvOverlay.objects.update_or_create(
            proc_spec=proc_spec,
            environment_name=env_name,
            defaults={
                "plan_name": plan_name,
                "target_replicas": target_replicas,
                "autoscaling": autoscaling,
                "scaling_config": scaling_config_dict,
                "tenant_id": proc_spec.tenant_id,
            },
        )


class ProcessSpecEnvOverlay(TimestampedModel):
    """进程定义中允许按环境覆盖的配置"""

    proc_spec = models.ForeignKey(
        ModuleProcessSpec, on_delete=models.CASCADE, db_constraint=False, related_name="env_overlays"
    )
    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=AppEnvName.get_choices(), null=False, max_length=16
    )

    target_replicas = models.IntegerField("期望副本数", null=True)
    plan_name = models.CharField(help_text="仅存储方案名称", max_length=32, null=True, blank=True)
    autoscaling = models.BooleanField("是否启用自动扩缩容", null=True)
    scaling_config: Optional[AutoscalingConfig] = AutoscalingConfigField("自动扩缩容配置", null=True)

    tenant_id = tenant_id_field_factory()

    objects = ProcessSpecEnvOverlayManager()

    class Meta:
        unique_together = ("proc_spec", "environment_name")


class ModuleDeployHookManager(models.Manager):
    """ModuleDeployHook RelatedManager, should be used by `module.deploy_hooks`"""

    def _get_caller(self) -> Module:
        if not hasattr(self, "instance"):
            raise RuntimeError("Can only call method from RelatedManager.")

        if not isinstance(self.instance, Module):
            raise TypeError("Can only call from module.deploy_hooks")
        return self.instance

    def enable_hook(
        self,
        type_: DeployHookType,
        proc_command: Optional[str] = None,
        command: Optional[List[str]] = None,
        args: Optional[List[str]] = None,
    ) -> "ModuleDeployHook":
        """upsert a ModuleDeployHook with args, will auto enable it if it is disabled

        :param type_: 钩子类型
        :param proc_command: 进程启动命令(包含完整命令和参数的字符串), 只能与 command/args 二选一
        :param command: 容器执行命令
        :param args: 命令参数
        """
        module = self._get_caller()
        if proc_command is not None:
            hook, _ = self.update_or_create(
                module=module, type=type_, defaults={"proc_command": proc_command, "enabled": True}
            )
        elif not (command is None and args is None):
            hook, _ = self.update_or_create(
                module=module,
                type=type_,
                defaults={"command": command, "args": args, "enabled": True, "proc_command": None},
            )
        else:
            raise ValueError("invalid value to upsert ModuleDeployHook")
        return hook

    def disable_hook(self, type_: DeployHookType) -> "ModuleDeployHook":
        """disable a ModuleDeployHook by type

        :raise ObjectDoesNotExist: if hook not found
        """
        module = self._get_caller()
        hook, _ = self.update_or_create(module=module, type=type_, defaults={"enabled": False})
        return hook

    def get_by_type(self, type_: DeployHookType) -> Optional["ModuleDeployHook"]:
        """get hook by type, return None if not found"""
        module = self._get_caller()
        try:
            return self.get(module=module, type=type_)
        except ObjectDoesNotExist:
            return None


class ModuleDeployHook(TimestampedModel):
    """钩子命令"""

    module = models.ForeignKey(
        "modules.Module", on_delete=models.CASCADE, db_constraint=False, related_name="deploy_hooks"
    )
    type = models.CharField(help_text="钩子类型", max_length=20, choices=DeployHookType.get_choices())

    proc_command = models.TextField(
        help_text="进程启动命令(包含完整命令和参数的字符串), 只能与 command/args 二选一", null=True
    )
    command: Optional[List[str]] = models.JSONField(help_text="容器执行命令", default=None, null=True)
    args: Optional[List[str]] = models.JSONField(help_text="命令参数", default=None, null=True)
    enabled = models.BooleanField(help_text="是否已开启", default=False)

    tenant_id = tenant_id_field_factory()

    objects = ModuleDeployHookManager()

    class Meta:
        unique_together = ("module", "type")

    def get_proc_command(self) -> str:
        if self.proc_command is not None:
            return self.proc_command
        # FIXME: proc_command 并不能简单地通过 shlex.join 合并 command 和 args 生成, 可能出现无法正常运行的问题
        return (shlex.join(self.command or []) + " " + shlex.join(self.args or [])).strip()

    def get_command(self) -> List[str]:
        if self.proc_command:
            return [shlex.split(self.proc_command)[0]]
        return self.command or []

    def get_args(self) -> List[str]:
        if self.proc_command:
            return shlex.split(self.proc_command)[1:]
        return self.args or []


BkSaaSField = make_json_field("BkSaaSField", List[SvcDiscEntryBkSaaS])
NameServersField = make_json_field("NameServersField", List[str])
HostAliasesField = make_json_field("HostAliasesField", List[HostAlias])


class SvcDiscConfig(AuditedModel):
    """服务发现配置"""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, db_constraint=False, unique=True)
    bk_saas: List[SvcDiscEntryBkSaaS] = BkSaaSField(default=list, help_text="")

    tenant_id = tenant_id_field_factory()


class DomainResolution(AuditedModel):
    """域名解析配置"""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, db_constraint=False, unique=True)

    nameservers: List[str] = NameServersField(default=list, help_text="k8s dnsConfig nameServers")
    host_aliases: List[HostAlias] = HostAliasesField(default=list, help_text="k8s hostAliases")

    tenant_id = tenant_id_field_factory()


def get_svc_disc_as_env_variables(env: ModuleEnvironment) -> Dict[str, str]:
    """Get SvcDiscConfig as env variables"""
    try:
        svc_disc = SvcDiscConfig.objects.get(application=env.application)
    except SvcDiscConfig.DoesNotExist:
        return {}

    if not svc_disc.bk_saas:
        return {}
    return BkSaaSEnvVariableFactory(
        [SvcDiscEntryBkSaaS(bk_app_code=item.bk_app_code, module_name=item.module_name) for item in svc_disc.bk_saas]
    ).make()


MonitoringField = make_json_field("MonitoringField", Monitoring)


class ObservabilityConfigManager(models.Manager):
    """Custom manager for ObservabilityConfig"""

    def upsert_by_module(self, module: Module, monitoring: Optional[Monitoring] = None):
        try:
            obj = ObservabilityConfig.objects.get(module=module)
        except ObservabilityConfig.DoesNotExist:
            return (
                ObservabilityConfig.objects.create(module=module, monitoring=monitoring, tenant_id=module.tenant_id),
                True,
            )
        else:
            last_monitoring = obj.monitoring
            obj.monitoring = monitoring
            obj.last_monitoring = last_monitoring
            obj.save(update_fields=["monitoring", "last_monitoring", "updated"])
            return obj, False


class ObservabilityConfig(TimestampedModel):
    module = models.OneToOneField(
        "modules.Module", on_delete=models.CASCADE, null=True, related_name="observability", db_constraint=False
    )
    monitoring: Optional[Monitoring] = MonitoringField("监控配置", default=None, null=True)
    last_monitoring: Optional[Monitoring] = MonitoringField("最近的一次监控配置", default=None, null=True)

    tenant_id = tenant_id_field_factory()

    objects = ObservabilityConfigManager()

    @property
    def monitoring_metrics(self) -> List[Metric]:
        """当前监控 metric 列表"""
        if self.monitoring:
            return self.monitoring.metrics or []
        return []

    @property
    def metric_processes(self) -> List[str]:
        """当前监控 metric 的进程名列表"""
        if not self.monitoring or not self.monitoring.metrics:
            return []

        return [metric.process for metric in self.monitoring.metrics]

    @property
    def last_metric_processes(self) -> List[str]:
        """最近一次监控 metric 的进程名列表"""
        if not self.last_monitoring or not self.last_monitoring.metrics:
            return []

        return [metric.process for metric in self.last_monitoring.metrics]


class BkAppManagedFields(TimestampedModel):
    """This model stores the management status of the fields of a module's bkapp model, it's
    helpful for resolve conflicts when some fields are managed by multiple managers.
    """

    module = models.ForeignKey(
        "modules.Module", on_delete=models.CASCADE, related_name="managed_fields", db_constraint=False
    )
    manager = models.CharField(help_text="管理者类型", max_length=20)
    fields = models.JSONField(help_text="所管理的字段", default=[])

    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("module", "manager")
