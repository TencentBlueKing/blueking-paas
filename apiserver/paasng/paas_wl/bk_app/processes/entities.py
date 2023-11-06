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
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from kubernetes.dynamic import ResourceField

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import Release
from paas_wl.bk_app.applications.models.managers import AppConfigVarManager
from paas_wl.bk_app.processes.serializers import InstanceDeserializer, ProcessDeserializer, ProcessSerializer
from paas_wl.core.app_structure import get_structure
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.generation.version import AppResVerManager
from paas_wl.infras.resources.kube_res.base import AppEntity, Schedule
from paas_wl.infras.resources.utils.basic import get_full_node_selector, get_full_tolerations
from paas_wl.workloads.images.utils import make_image_pull_secret_name
from paas_wl.workloads.release_controller.constants import ImagePullPolicy


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
    # 由于 command/args 本身经过了镜像启动脚本的封装
    # 所以这里我们额外存储一个用户填写的启动命令
    # 假设 procfile 中是 `web: python manage.py runserver`
    # 则 command: ['bash', '/runner/init']
    #    args: ["start", "web"]
    #    proc_command: "python manage.py runserver"
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
        build = release.build
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
            replicas=get_structure(release.app).get(type_, 0),
            runtime=Runtime(
                envs=envs,
                image=build.get_image(),
                command=build.get_entrypoint_for_proc(type_),
                args=build.get_command_for_proc(type_, procfile[type_]),
                proc_command=procfile[type_],
                image_pull_policy=config.runtime.get_image_pull_policy(),
                image_pull_secrets=[{"name": make_image_pull_secret_name(wl_app=release.app)}],
            ),
            schedule=Schedule(
                node_selector=get_full_node_selector(release.app, config),
                tolerations=get_full_tolerations(release.app, config),
                cluster_name=get_cluster_by_app(release.app).name,
            ),
            resources=Resources(**config.resource_requirements.get(type_, {})),
        )
        process.name = mapper_version.deployment(process=process).name
        return process

    @property
    def main_container_name(self) -> str:
        # TODO: 统一主容器的名字
        if self.app.type == WlAppType.DEFAULT:
            return f"{self.app.region}-{self.app.scheduler_safe_name}"
        return self.type

    @property
    def available_instance_count(self):
        return sum(1 for instance in self.instances if instance.ready and instance.version == self.version)

    def fulfill_runtime(self, replicas: int, success: int, metadata: 'ResourceField' = None):
        """填充运行时具体信息"""
        self.status = Status(replicas=replicas, success=success, failed=max(replicas - success, 0))
        self.metadata = metadata
