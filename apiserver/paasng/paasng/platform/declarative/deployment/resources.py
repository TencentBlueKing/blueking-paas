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

from typing import Dict, Optional

from attrs import define

from paasng.platform.applications.constants import AppLanguage
from paasng.platform.bkapp_model.entities import Process, v1alpha2
from paasng.platform.declarative.constants import AppSpecVersion


@define
class BluekingMonitor:
    """Resource: BluekingMonitor

    :param port: Service 暴露的端口号
    :param target_port: Service 关联的容器内的端口号, 不设置则使用 port
    """

    port: int
    target_port: Optional[int] = None

    def __attrs_post_init__(self):
        if self.target_port is None:
            self.target_port = self.port


@define
class DeploymentDesc:
    """Deployment description object, contains spec data related with deployment.

    :param language: 应用开发语言
    :param source_dir: 源码目录
    :param bk_monitor: SaaS 监控采集配置
    :param spec_version: 描述文件版本
    :param spec: BkAppSpec
    """

    language: AppLanguage
    spec: v1alpha2.BkAppSpec
    source_dir: str = ""
    # TODO: BkAppSpec 支持该配置
    bk_monitor: Optional[BluekingMonitor] = None
    spec_version: AppSpecVersion = AppSpecVersion.VER_2

    def get_procfile(self) -> Dict[str, str]:
        return {proc_type: process.get_proc_command() for proc_type, process in self.get_processes().items()}

    def get_processes(self) -> Dict[str, Process]:
        """Get the Process objects. These objects are used to synchronize with the
        application model and to create processes when a new release is issued.
        """
        # TODO/FIXME: 让函数接受当前环境 environment 参数，因为对于一份完整的应用描述来说，
        # 可能针对不同环境配置了不同的值（通过 envOverlay），这些值包括 replicas, plan 等。
        # 以此不同的环境可能会又不同的 replicas 设置。
        #
        # 而这又带来了其他问题：配置解析阶段，因为 deployment 上下文的存在，这里可以拿到和
        # 当前环境强相关的进程对象。但是到了后续的将进程数据同步到 ModuleProcessSpec 时，
        # 由于 Process 并没有环境信息（ModuleProcessSpecManager 也不接受），因此这套同步
        # 实际上存在缺陷。
        #
        # 可能的解决方案：
        #
        # - 此处返回的 Process 和环境相关，ModuleProcessSpecManager 也接受带环境的同步
        # - 同步进程时，不包含除 name 和 command 以外的其他信息，比如可能环境相关的 replicas 等
        #
        result = {}
        for process in self.spec.processes:
            # TODO: Try read envOverlay to get the "replicas" and "plan" values
            result[process.name] = process
        return result
