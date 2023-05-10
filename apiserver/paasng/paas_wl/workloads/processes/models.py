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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

from django.conf import settings
from django.db import models
from jsonfield import JSONField
from kubernetes.dynamic import ResourceField

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.platform.applications.constants import WlAppType
from paas_wl.platform.applications.models.managers import AppConfigVarManager
from paas_wl.platform.applications.models.managers.app_metadata import get_metadata
from paas_wl.platform.applications.models.managers.app_res_ver import AppResVerManager
from paas_wl.release_controller.constants import ImagePullPolicy
from paas_wl.resources.base import kres
from paas_wl.resources.kube_res.base import AppEntity, Schedule
from paas_wl.resources.utils.basic import get_full_node_selector, get_full_tolerations
from paas_wl.utils.models import TimestampedModel
from paas_wl.workloads.images.constants import PULL_SECRET_NAME
from paas_wl.workloads.processes.constants import ProcessTargetStatus
from paas_wl.workloads.processes.serializers import InstanceDeserializer, ProcessDeserializer, ProcessSerializer

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import Release, WlApp

logger = logging.getLogger(__name__)

# Django models start
# All models was originally defined in PaaSNG Service

PROC_DEFAULT_REPLICAS = 1


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
    name = models.CharField('进程规格方案名称', max_length=32, db_index=True)
    max_replicas = models.IntegerField('最大副本数')
    limits = JSONField(default={})
    requests = JSONField(default={})
    is_active = models.BooleanField(verbose_name='是否可用', default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ProcessSpecPlanManager()

    class Meta:
        get_latest_by = 'created'

    def get_resource_summary(self):
        return {'limits': self.limits, 'requests': self.requests}

    def __str__(self):
        return self.name


class ProcessSpec(TimestampedModel):
    name = models.CharField('进程名称', max_length=32)
    type = models.CharField('计算单元组类型（deprecated）', max_length=32)
    engine_app = models.ForeignKey(
        'api.App', on_delete=models.DO_NOTHING, db_constraint=False, related_name='process_specs'
    )
    target_replicas = models.IntegerField('期望副本数', default=1)
    target_status = models.CharField('期望状态', max_length=32, default="start")
    plan = models.ForeignKey(ProcessSpecPlan, on_delete=models.CASCADE)
    autoscaling = models.BooleanField('是否启用自动扩缩容', default=False)
    scaling_config = JSONField('自动扩缩容配置', default={})

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


class ProcessSpecManager:
    def __init__(self, wl_app: 'WlApp'):
        self.wl_app = wl_app

    def sync(self, processes: List['ProcessTmpl']):
        """Sync ProcessSpecs data with given processes.

        :param processes: plain process spec structure,
                          such as [{"name": "web", "command": "foo", "replicas": 1, "plan": "bar"}, ...]
                          where 'replicas' and 'plan' is optional
        """
        processes_map: Dict[str, 'ProcessTmpl'] = {process.name: process for process in processes}
        environment = get_metadata(self.wl_app).environment

        # Hardcode proc_type to "process" because no other values is supported at this moment.
        proc_type = 'process'
        proc_specs = ProcessSpec.objects.filter(engine_app=self.wl_app, type=proc_type)
        existed_procs_name = set(proc_specs.values_list('name', flat=True))

        # remove proc spec objects which is already deleted via procfile
        removing_procs_name = list(existed_procs_name - processes_map.keys())
        if removing_procs_name:
            proc_specs.filter(name__in=removing_procs_name).delete()

        default_process_spec_plan = ProcessSpecPlan.objects.get_by_name(name=settings.DEFAULT_PROC_SPEC_PLAN)

        # add spec objects which is added via procfile
        adding_proc_specs = [process for name, process in processes_map.items() if name not in existed_procs_name]
        spec_create_bulks = []
        for process in adding_proc_specs:
            target_replicas = process.replicas or self.get_default_replicas(process.name, environment)
            plan = default_process_spec_plan
            if plan_name := process.plan:
                plan = self.get_plan(plan_name, default_process_spec_plan)

            process_spec = ProcessSpec(
                type=proc_type,
                region=self.wl_app.region,
                name=process.name,
                engine_app_id=self.wl_app.pk,
                target_replicas=target_replicas,
                plan=plan,
            )
            spec_create_bulks.append(process_spec)
        if spec_create_bulks:
            ProcessSpec.objects.bulk_create(spec_create_bulks)

        # update spec objects
        updating_proc_specs = [process for name, process in processes_map.items() if name in existed_procs_name]
        spec_update_bulks = []
        for process in updating_proc_specs:
            process_spec = proc_specs.get(name=process.name)
            changed = False
            if plan_name := process.plan:
                if plan := self.get_plan(plan_name, None):
                    changed = True
                    process_spec.plan = plan
            if replicas := process.replicas:
                changed = True
                process_spec.target_replicas = replicas
            if changed:
                spec_update_bulks.append(process_spec)
        if spec_update_bulks:
            ProcessSpec.objects.bulk_update(spec_update_bulks, ["target_replicas", "plan", "updated"])

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


def initialize_default_proc_spec_plans():
    """Initialize default process spec plan objects which were defined in settings"""
    plans = settings.DEFAULT_PROC_SPEC_PLANS

    for name, config in plans.items():
        try:
            ProcessSpecPlan.objects.get_by_name(name=name)
            logger.debug(f'Plan: {name} already exists in region, skip initialization.')
        except ProcessSpecPlan.DoesNotExist:
            logger.info(f'Creating default plan: {name}...')
            ProcessSpecPlan.objects.create(name=name, **config)


# Django models end


@dataclass
class ProcessTmpl:
    """This class declare a process template which can be used to sync process spec or deploy a process(deployment)

    :param command: 启动指令
    :param replicas: 副本数
    :param plan: 资源方案名称
    """

    name: str
    command: str
    replicas: Optional[int] = None
    plan: Optional[str] = None

    def __post_init__(self):
        self.name = self.name.lower()


@dataclass
class Resources:
    """计算资源定义"""

    @dataclass
    class Spec:
        cpu: str
        memory: str

    limits: Optional[Spec] = None
    requests: Optional[Spec] = None


@dataclass
class Runtime:
    """运行相关"""

    envs: Dict[str, str]
    image: str
    # 实际的镜像启动命令
    command: List[str]
    args: List[str]
    # [deprecated] TODO: 删除 proc_command 以及与其相关的字段
    # 由于 command 本身经过了镜像启动脚本的封装
    # 所以这里我们额外存储一个用户填写的启动命令
    # 类似 procfile 中是 web: python manage.py runserver
    # command: ./init.sh start web
    # proc_command: python manage.py runserver
    proc_command: str = ""
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.IF_NOT_PRESENT)
    image_pull_secrets: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Probe:
    type: str = "common"
    params: dict = field(default_factory=dict)


@dataclass
class Status:
    replicas: int
    success: int = 0
    failed: int = 0

    version: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {'replicas': self.replicas, 'success': self.success, 'failed': self.failed}


@dataclass
class Instance(AppEntity):
    """副本实例定义

    肩负着内部程序流转和 K8S 交互的重任

    :param process_type: 进程类型
    :param host_ip: Pod 分配的 host_ip
    :param start_time: 启动时间
    :param state: Pod 的状态
    :param state_message: Pod 处于 Terminated, Waiting 的原因
    :param image: 当前进程使用的镜像, 即主容器使用的镜像
    :param envs: 直接在 Pod 中声明的环境变量
    :param ready: 进程实例是否就绪
    :param restart_count: 重启次数
    :param version: 当前实例的版本号, 每次部署递增
    """

    process_type: str
    host_ip: str = ""
    start_time: str = ""
    state: str = ""
    state_message: str = ""
    image: str = ""
    envs: Dict[str, str] = field(default_factory=dict)
    ready: bool = True
    restart_count: int = 0

    version: int = 0

    class Meta:
        kres_class = kres.KPod
        deserializer = InstanceDeserializer

    @property
    def shorter_name(self) -> str:
        """Return a simplified name

        'ieod-x-gunicorn-deployment-59b9789f76wk82' -> '59b9789f76wk82'
        """
        return self.get_shorter_instance_name(self.name)

    @classmethod
    def get_shorter_instance_name(cls, instance_name: str) -> str:
        return instance_name.split('-')[-1]


@dataclass
class Process(AppEntity):
    """进程定义

    肩负着内部程序流转和 K8S 交互的重任
    """

    version: int
    replicas: int
    type: str
    schedule: Schedule
    runtime: Runtime
    resources: Optional[Resources] = None
    readiness_probe: Optional[Probe] = None

    # 实际资源的动态状态
    metadata: Optional['ResourceField'] = None
    status: Optional[Status] = None
    instances: List[Instance] = field(default_factory=list)

    class Meta:
        kres_class = kres.KDeployment
        deserializer = ProcessDeserializer
        serializer = ProcessSerializer

    @classmethod
    def from_release(cls, type_: str, release: 'Release', extra_envs: Optional[dict] = None) -> 'Process':
        """通过 release 生成 Process"""
        config = release.config
        procfile = release.get_procfile()
        envs = AppConfigVarManager(app=release.app).get_process_envs(type_)
        envs.update(release.get_envs())
        envs.update(extra_envs or {})

        mapper_version = AppResVerManager(release.app).curr_version
        process = Process(
            app=release.app,
            # AppEntity.name should be the name of k8s resource
            name="should-set-by-mapper",
            type=type_,
            version=release.version,
            replicas=release.app.get_structure().get(type_, 0),
            runtime=Runtime(
                envs=envs,
                image=config.get_image(),
                command=config.runtime.get_entrypoint(),
                args=config.runtime.get_command(type_, procfile),
                proc_command=procfile[type_],
                image_pull_policy=config.runtime.get_image_pull_policy(),
                image_pull_secrets=[{"name": PULL_SECRET_NAME}],
            ),
            schedule=Schedule(
                node_selector=get_full_node_selector(release.app, config),
                tolerations=get_full_tolerations(release.app, config),
                cluster_name=get_cluster_by_app(release.app).name,
            ),
            resources=Resources(**config.resource_requirements.get(type_, {})),
        )
        # TODO: 解决 MapperVersion 与 Process 循环依赖的问题
        process.name = mapper_version.deployment(process=process).name
        return process

    @property
    def main_container_name(self) -> str:
        # TODO: 统一主容器的名字
        if self.app.type == WlAppType.DEFAULT:
            return f"{self.app.region}-{self.app.scheduler_safe_name}"
        return self.type

    def fulfill_runtime(self, replicas: int, success: int, metadata: 'ResourceField' = None):
        """填充运行时具体信息"""
        self.status = Status(replicas=replicas, success=success, failed=max(replicas - success, 0))
        self.metadata = metadata
