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
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from cattr import unstructure
from django.conf import settings
from django.db import models
from jsonfield import JSONField

from paas_wl.bk_app.applications.models.managers.app_metadata import get_metadata
from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP, PLAN_TO_REQUEST_QUOTA_MAP
from paas_wl.bk_app.processes.constants import DEFAULT_CNATIVE_MAX_REPLICAS, ProbeType, ProcessTargetStatus
from paas_wl.core.app_structure import set_global_get_structure
from paas_wl.utils.models import TimestampedModel
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paasng.platform.declarative.deployment.resources import ProbeHandler
from paasng.utils.models import make_json_field

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp

logger = logging.getLogger(__name__)


PROC_DEFAULT_REPLICAS = 1
AutoscalingConfigField = make_json_field("AutoscalingConfigField", AutoscalingConfig)


class ProcessSpecPlanManager(models.Manager):
    def get_by_name(self, name: str):
        """get object by name
        由于历史原因, 可能会存在相同名字的 Plan, 此时使用第一个方案
        """
        try:
            return self.get(name=name)
        except ProcessSpecPlan.MultipleObjectsReturned:
            return self.filter(name=name).first()


class ProcessSpecPlan(models.Model):
    name = models.CharField("进程规格方案名称", max_length=32, db_index=True)
    max_replicas = models.IntegerField("最大副本数")
    limits = JSONField(default={})
    requests = JSONField(default={})
    is_active = models.BooleanField(verbose_name="是否可用", default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ProcessSpecPlanManager()

    class Meta:
        get_latest_by = "created"

    def get_resource_summary(self):
        return {"limits": self.limits, "requests": self.requests}

    def __str__(self):
        return self.name


class ProcessSpec(TimestampedModel):
    name = models.CharField("进程名称", max_length=32)
    type = models.CharField("计算单元组类型（deprecated）", max_length=32)
    engine_app = models.ForeignKey(
        "api.App", on_delete=models.DO_NOTHING, db_constraint=False, related_name="process_specs"
    )

    proc_command = models.TextField(
        help_text="进程启动命令(包含完整命令和参数的字符串), 只能与 command/args 二选一", null=True
    )
    command: List[str] = models.JSONField(help_text="容器执行命令", default=None, null=True)
    args: List[str] = models.JSONField(help_text="命令参数", default=None, null=True)
    port = models.IntegerField(help_text="容器端口", null=True)

    # Deprecated: 仅用于 v1alpha1 的云原生应用
    image = models.CharField(help_text="容器镜像, 仅用于 v1alpha1 的云原生应用", max_length=255, null=True)
    image_pull_policy = models.CharField(
        help_text="镜像拉取策略(仅用于 v1alpha1 的云原生应用)",
        choices=ImagePullPolicy.get_choices(),
        default=ImagePullPolicy.IF_NOT_PRESENT,
        max_length=20,
    )
    image_credential_name = models.CharField(
        help_text="镜像拉取凭证名(仅用于 v1alpha1 的云原生应用)", max_length=64, null=True
    )

    target_replicas = models.IntegerField("期望副本数", default=1)
    target_status = models.CharField("期望状态", max_length=32, default="start")
    plan = models.ForeignKey(ProcessSpecPlan, on_delete=models.CASCADE)
    autoscaling = models.BooleanField("是否启用自动扩缩容", default=False)
    scaling_config: Optional[AutoscalingConfig] = AutoscalingConfigField("自动扩缩容配置", null=True)

    def save(self, *args, **kwargs):
        if self.target_replicas > self.plan.max_replicas:
            raise ValueError("target_replicas is more than plan max_replicas")
        super().save(*args, **kwargs)

    def __str__(self):
        return "{application}-{type}-{name}".format(application=self.engine_app.name, type=self.type, name=self.name)

    @property
    def computed_replicas(self) -> int:
        if self.target_status == ProcessTargetStatus.STOP:
            return 0
        return self.target_replicas


class AttrSetter:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.changed = False

    def setattr(self, name, value):
        setattr(self.wrapped, name, value)
        self.changed = True


class ProcessSpecManager:
    def __init__(self, wl_app: "WlApp"):
        self.wl_app = wl_app

    def sync(self, processes: List["ProcessTmpl"]):
        """Sync ProcessSpecs data with given processes.

        :param processes: plain process spec structure,
                          such as [{"name": "web", "command": "foo", "replicas": 1, "plan": "bar"}, ...]
                          where 'replicas' and 'plan' is optional
        """
        processes_map: Dict[str, "ProcessTmpl"] = {process.name: process for process in processes}
        environment = get_metadata(self.wl_app).environment

        # Hardcode proc_type to "process" because no other values is supported at this moment.
        proc_type = "process"
        proc_specs = ProcessSpec.objects.filter(engine_app=self.wl_app, type=proc_type)
        existed_procs_name = set(proc_specs.values_list("name", flat=True))

        # remove proc spec objects which is already deleted via procfile
        removing_procs_name = list(existed_procs_name - processes_map.keys())
        if removing_procs_name:
            proc_specs.filter(name__in=removing_procs_name).delete()

        # add spec objects start
        default_process_spec_plan = ProcessSpecPlan.objects.get_by_name(name=settings.DEFAULT_PROC_SPEC_PLAN)
        adding_procs = [process for name, process in processes_map.items() if name not in existed_procs_name]

        def process_spec_builder(process: "ProcessTmpl") -> ProcessSpec:
            target_replicas = process.replicas or self.get_default_replicas(process.name, environment)
            plan = default_process_spec_plan
            if plan_name := process.plan:
                plan = self.get_plan(plan_name, default_process_spec_plan)

            return ProcessSpec(
                type=proc_type,
                region=self.wl_app.region,
                name=process.name,
                engine_app_id=self.wl_app.pk,
                target_replicas=target_replicas,
                plan=plan,
                proc_command=process.command,
                autoscaling=process.autoscaling,
                scaling_config=process.scaling_config,
            )

        self.bulk_create_procs(proc_creator=process_spec_builder, adding_procs=adding_procs)
        # add spec objects end

        # update spec objects
        updating_proc_specs = [process for name, process in processes_map.items() if name in existed_procs_name]

        def process_spec_updator(process: "ProcessTmpl") -> Tuple[bool, ProcessSpec]:
            process_spec = proc_specs.get(name=process.name)
            recorder = AttrSetter(process_spec)
            if (command := process.command) and command != process_spec.proc_command:
                recorder.setattr("proc_command", command)
            if (plan_name := process.plan) and (plan := self.get_plan(plan_name, None)):
                recorder.setattr("plan", plan)
            elif process.autoscaling != process_spec.autoscaling:
                recorder.setattr("autoscaling", process.autoscaling)
            elif (scaling_config := process.scaling_config) and scaling_config != process_spec.scaling_config:
                recorder.setattr("autoscaling", scaling_config)
            elif (replicas := process.replicas) and replicas != process_spec.target_replicas:
                recorder.setattr("target_replicas", replicas)
            return recorder.changed, process_spec

        self.bulk_update_procs(
            proc_updator=process_spec_updator,
            updating_procs=updating_proc_specs,
            updated_fields=[
                "proc_command",
                "target_replicas",
                "target_replicas",
                "plan",
                "scaling_config",
                "autoscaling",
                "updated",
            ],
        )

    def bulk_create_procs(
        self,
        proc_creator: Callable[["ProcessTmpl"], ProcessSpec],
        adding_procs: List["ProcessTmpl"],
    ):
        """bulk create ProcessSpec

        :param proc_creator: ProcessSpec factory, accept `process` and return ProcessSpec
        :param adding_procs: `process` waiting to transform to ProcessSpec
        """
        spec_create_bulks: List[ProcessSpec] = []
        for process in adding_procs:
            spec_create_bulks.append(proc_creator(process))
        if spec_create_bulks:
            ProcessSpec.objects.bulk_create(spec_create_bulks)

    def bulk_update_procs(
        self,
        proc_updator: Callable[["ProcessTmpl"], Tuple[bool, ProcessSpec]],
        updating_procs: List["ProcessTmpl"],
        updated_fields: List[str],
    ):
        """bulk update ProcessSpec

        :param proc_updator: handler to update ProcessSpec,
                            accept `process` and return Tuple[whether spec need updated, updatedProcessSpec]
        :param updating_procs: `process` waiting to update
        """
        spec_update_bulks: List[ProcessSpec] = []
        for process in updating_procs:
            changed, updated = proc_updator(process)
            if changed:
                spec_update_bulks.append(updated)
        if spec_update_bulks:
            ProcessSpec.objects.bulk_update(spec_update_bulks, updated_fields)

    @staticmethod
    def get_default_replicas(process_type: str, environment: str):
        """Get default replicas for current process type"""
        return settings.ENGINE_PROC_REPLICAS_BY_TYPE.get((process_type, environment), PROC_DEFAULT_REPLICAS)

    @staticmethod
    def get_plan(plan_name: str, default: Optional[ProcessSpecPlan]) -> Optional[ProcessSpecPlan]:
        """Get plan by name, if not found, return default one"""
        try:
            return ProcessSpecPlan.objects.get_by_name(name=plan_name)
        except ProcessSpecPlan.DoesNotExist:
            return default


def _get_structure(app: "WlApp") -> Dict:
    return {item.name: item.computed_replicas for item in ProcessSpec.objects.filter(engine_app_id=app.uuid)}


# Set the "get_structure" function to current implementation
set_global_get_structure(_get_structure)


@dataclass
class ProcessTmpl:
    """This class declare a process template which can be used to sync process spec or deploy a process(deployment)

    :param command: 启动指令
    :param replicas: 副本数
    :param plan: 资源方案名称
    :param autoscaling: 是否开启自动扩缩容
    :param scaling_config: 自动扩缩容配置
    """

    name: str
    command: str
    replicas: Optional[int] = None
    plan: Optional[str] = None
    autoscaling: bool = False
    scaling_config: Optional[AutoscalingConfig] = None

    def __post_init__(self):
        self.name = self.name.lower()


ProbeHandlerField = make_json_field("ProbeHandlerField", ProbeHandler)


class ProcessProbe(models.Model):
    app = models.ForeignKey("api.App", related_name="process_probe", on_delete=models.CASCADE, db_constraint=False)
    # 探针应该与 process 匹配 （Process 定义里面就是将配置里面的 key 转换为 type ，因此这里与 process 定义同步，取名 process_type）
    process_type = models.CharField(max_length=255)
    probe_type = models.CharField(max_length=255, choices=ProbeType.get_django_choices())

    probe_handler = ProbeHandlerField(default=dict, help_text="具体的检测机制配置，例如 httpGet 完整配置")
    initial_delay_seconds = models.IntegerField(default=0)
    timeout_seconds = models.PositiveIntegerField(default=1)
    period_seconds = models.PositiveIntegerField(default=10)
    success_threshold = models.PositiveIntegerField(default=1)
    failure_threshold = models.PositiveIntegerField(default=3)

    class Meta:
        unique_together = ("app", "process_type", "probe_type")


def initialize_default_proc_spec_plans():
    """Initialize default process spec plan objects which were defined in settings"""
    plans = settings.DEFAULT_PROC_SPEC_PLANS

    for name, config in plans.items():
        try:
            ProcessSpecPlan.objects.get_by_name(name=name)
            logger.debug(f"Plan: {name} already exists, skip initialization.")
        except ProcessSpecPlan.DoesNotExist:
            logger.info(f"Creating default plan: {name}...")
            ProcessSpecPlan.objects.create(name=name, **config)

    for cnative_plan in ResQuotaPlan.get_values():
        try:
            ProcessSpecPlan.objects.get_by_name(name=cnative_plan)
            logger.debug(f"Plan: {cnative_plan} already exists, skip initialization.")
        except ProcessSpecPlan.DoesNotExist:
            logger.info(f"Creating default plan: {cnative_plan}...")
            ProcessSpecPlan.objects.create(
                name=cnative_plan,
                max_replicas=DEFAULT_CNATIVE_MAX_REPLICAS,
                limits=unstructure(PLAN_TO_LIMIT_QUOTA_MAP[cnative_plan]),
                requests=unstructure(PLAN_TO_REQUEST_QUOTA_MAP[cnative_plan]),
            )
