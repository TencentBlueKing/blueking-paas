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
import datetime
import logging
from dataclasses import dataclass
from typing import Dict, Optional

import arrow
import cattr
from django.conf import settings
from kubernetes.dynamic import ResourceField, ResourceInstance
from typing_extensions import Literal

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.applications.models.managers.app_configvar import AppConfigVarManager
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resource_templates.logging import get_app_logging_volume, get_app_logging_volume_mounts
from paas_wl.infras.resource_templates.utils import AddonManager
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import (
    AppEntity,
    AppEntityDeserializer,
    AppEntityManager,
    AppEntitySerializer,
    Schedule,
)
from paas_wl.infras.resources.kube_res.envs import decode_envs, encode_envs
from paas_wl.infras.resources.utils.basic import get_full_node_selector, get_full_tolerations
from paas_wl.utils.kubestatus import (
    check_pod_health_status,
    get_container_fail_message,
    parse_container_status,
    parse_pod,
)
from paas_wl.workloads.images.utils import make_image_pull_secret_name
from paas_wl.workloads.release_controller.entities import ContainerRuntimeSpec
from paas_wl.workloads.release_controller.hooks.entities import CommandKubeAdaptor
from paas_wl.workloads.release_controller.hooks.models import Command as CommandModel

logger = logging.getLogger(__name__)


class CommandDeserializer(AppEntityDeserializer['Command']):
    api_version = "v1"

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> 'Command':
        main_container = self._get_main_container(kube_data)
        annotations = kube_data.metadata.get('annotations', {})

        pod_status = kube_data.status
        health_status = check_pod_health_status(parse_pod(kube_data))

        if hasattr(pod_status, "startTime"):
            start_time = arrow.get(pod_status.startTime)
        else:
            logger.warning(
                "Pod<%s/%s> missing start_time field!", kube_data.metadata.namespace, kube_data.metadata.name
            )
            start_time = None

        main_container_exit_code = None
        main_container_fail_message = None
        if raw_main_container_status := self._get_main_container_status(kube_data):
            main_container_status = parse_container_status(raw_main_container_status)
            main_container_fail_message = get_container_fail_message(main_container_status)
            if main_container_status.state.terminated:
                main_container_exit_code = main_container_status.state.terminated.exit_code

        return Command(
            # Pod 描述性信息
            app=app,
            name=kube_data.metadata.name,
            runtime=ContainerRuntimeSpec(
                image=main_container.image,
                command=main_container.command,
                args=main_container.args,
                envs=decode_envs(main_container.env),
                image_pull_policy=main_container.imagePullPolicy,
                image_pull_secrets=getattr(kube_data.spec, "imagePullSecrets", None) or [],
            ),
            schedule=Schedule(
                cluster_name=annotations["cluster_name"],
                node_selector=getattr(kube_data.spec, "node_selector", {}),
                tolerations=getattr(kube_data.spec, "tolerations", []),
            ),
            # 持久化字段(annotations)
            pk=annotations["pk"],
            type_=annotations["type"],
            version=int(annotations["version"]),
            # 运行时信息
            start_time=start_time,
            phase=pod_status.phase,
            phase_message=health_status.message,
            main_container_exit_code=main_container_exit_code,
            main_container_fail_message=main_container_fail_message,
        )

    @staticmethod
    def _get_main_container(pod_info: ResourceInstance) -> ResourceField:
        """获取 Pod 中声明的主容器信息."""
        # Note: 根据约定, 与 Pod 命名一致的容器为主容器
        main_container_name = pod_info.metadata.name
        for c in pod_info.spec.containers:
            if c.name == main_container_name:
                return c
        raise RuntimeError("container not found.")

    @staticmethod
    def _get_main_container_status(pod_info: ResourceInstance) -> Optional[ResourceField]:
        """获取 Pod 中声明的主容器的状态"""
        # Note: 根据约定, 与 Pod 命名一致的容器为主容器
        main_container_name = pod_info.metadata.name
        for c in pod_info.status.get("containerStatuses", []):
            if c.name == main_container_name:
                return c
        return None


class CommandSerializer(AppEntitySerializer['Command']):
    api_version = "v1"

    def serialize(self, obj: 'Command', original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        addon_mgr = AddonManager(obj.app)
        containers = [
            {
                'command': obj.runtime.command,
                'args': obj.runtime.args,
                'env': encode_envs(obj.runtime.envs),
                'image': obj.runtime.image,
                'name': obj.name,
                'imagePullPolicy': obj.runtime.image_pull_policy,
                'resources': self._get_pod_resources(obj),
                'volumeMounts': cattr.unstructure(
                    get_app_logging_volume_mounts(obj.app) + addon_mgr.get_volume_mounts()
                ),
            }
        ] + cattr.unstructure(addon_mgr.get_sidecars())

        pod_template = {
            'apiVersion': self.api_version,
            'kind': 'Pod',
            'metadata': {
                'name': obj.name,
                'namespace': obj.app.namespace,
                'labels': self._get_kube_labels(obj),
                'annotations': self._get_kube_annotations(obj),
            },
            'spec': {
                'containers': containers,
                'volumes': cattr.unstructure(get_app_logging_volume(obj.app) + addon_mgr.get_volumes()),
                'restartPolicy': 'Never',
                'nodeSelector': obj.schedule.node_selector,
                'tolerations': obj.schedule.tolerations,
                'imagePullSecrets': obj.runtime.image_pull_secrets,
            },
        }
        return pod_template

    def _get_kube_labels(self, obj: 'Command') -> Dict:
        return {'pod_selector': obj.name, 'category': "command"}

    def _get_kube_annotations(self, obj: 'Command') -> Dict:
        return {
            "type": obj.type_,
            "version": str(obj.version),
            "pk": obj.pk,
            "cluster_name": obj.schedule.cluster_name,
        }

    def _get_pod_resources(self, obj: 'Command'):
        return settings.SLUGBUILDER_RESOURCES_SPEC


@dataclass
class Command(AppEntity):
    """副本实例定义

    肩负着内部程序流转和 K8S 交互的重任

    :param runtime: Command(Pod) 运行相关配置, 例如主容器使用的镜像, 启动参数等
    :param schedule: Command(Pod) 调度相关的配置
    :param pk: 关联的数据库模型主键
    :param type_: 命令的类型, 目前仅支持 pre-release-hook
    :param version: 当前实例的版本号, 每次部署递增
    :param start_time: Command(Pod) 启动时间
    :param phase: Command(Pod) 的 phase
    :param phase_message: Command(Pod) 处于 phase 的原因
    :param main_container_exit_code: 主容器退出的状态码
    :param main_container_fail_message: 主容器执行失败的原因
    """

    runtime: ContainerRuntimeSpec
    schedule: Schedule
    # 持久化字段(annotations)
    pk: str
    type_: str
    version: int

    # 运行时状态
    start_time: Optional[datetime.datetime]
    phase: Literal["Pending", "Running", "Succeeded", "Failed", "Unknown"] = "Unknown"
    phase_message: Optional[str] = None
    main_container_exit_code: Optional[int] = None
    main_container_fail_message: Optional[str] = None

    class Meta:
        kres_class = kres.KPod
        deserializer = CommandDeserializer
        serializer = CommandSerializer

    @classmethod
    def from_db_obj(cls, command: 'CommandModel', extra_envs: Optional[Dict] = None) -> 'Command':
        envs = command.get_envs()
        envs.update(AppConfigVarManager(command.app).get_envs())
        envs.update(extra_envs or {})

        return cls(
            app=command.app,
            name=CommandKubeAdaptor(command).get_pod_name(),
            runtime=ContainerRuntimeSpec(
                image=command.build.get_image(),
                command=command.build.get_universal_entrypoint(),
                args=command.split_command,
                envs=envs,
                image_pull_policy=command.config.runtime.get_image_pull_policy(),
                image_pull_secrets=[{"name": make_image_pull_secret_name(wl_app=command.app)}],
            ),
            schedule=Schedule(
                cluster_name=get_cluster_by_app(command.app).name,
                node_selector=get_full_node_selector(command.app, command.config),
                tolerations=get_full_tolerations(command.app, command.config),
            ),
            pk=str(command.pk),
            type_=command.type,
            version=command.version,
            start_time=None,
        )


command_kmodel: AppEntityManager[Command] = AppEntityManager(Command)
