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

import datetime
import logging
from dataclasses import dataclass
from typing import Dict, Literal

from paas_wl.infras.cluster.utils import get_cluster_by_app
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity, AppEntityManager, Schedule
from paas_wl.infras.resources.utils.basic import (
    get_full_node_selector,
    get_full_tolerations,
    get_slugbuilder_resources,
)
from paas_wl.utils.env_vars import VarsRenderContext, render_vars_dict
from paas_wl.workloads.images.utils import make_image_pull_secret_name
from paas_wl.workloads.release_controller.entities import ContainerRuntimeSpec
from paas_wl.workloads.release_controller.hooks.entities import CommandKubeAdaptor
from paas_wl.workloads.release_controller.hooks.kres_slzs import CommandDeserializer, CommandSerializer
from paas_wl.workloads.release_controller.hooks.models import Command as CommandModel

logger = logging.getLogger(__name__)


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
    start_time: datetime.datetime | None
    phase: Literal["Pending", "Running", "Succeeded", "Failed", "Unknown"] = "Unknown"
    phase_message: str | None = None
    main_container_exit_code: int | None = None
    main_container_fail_message: str | None = None

    class Meta:
        kres_class = kres.KPod
        deserializer = CommandDeserializer
        serializer = CommandSerializer

    @classmethod
    def from_db_obj(cls, command: "CommandModel", extra_envs: Dict | None = None) -> "Command":
        envs = command.get_envs()
        envs.update(extra_envs or {})
        envs = render_vars_dict(envs, context=VarsRenderContext(process_type="sys-cmd"))

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
                # TODO: 之前 hook 一直使用的 slugbuilder 的资源配额，需要考虑是否改成独立配置？
                resources=get_slugbuilder_resources(command.app),
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
