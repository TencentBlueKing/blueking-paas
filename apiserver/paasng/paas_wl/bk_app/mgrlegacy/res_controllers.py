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
from typing import List

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.deploy.app_res.controllers import ProcessesHandler
from paas_wl.bk_app.processes.controllers import ProcessesInfo
from paas_wl.bk_app.processes.kres_entities import Process
from paas_wl.bk_app.processes.readers import instance_kmodel, process_kmodel
from paas_wl.infras.resources.base.base import EnhancedApiClient
from paas_wl.infras.resources.base.kres import KDeployment
from paas_wl.infras.resources.generation.mapper import MapperProcConfig
from paas_wl.infras.resources.utils.basic import get_client_by_app


class DefaultAppProcessController:
    """普通应用迁移至云原生时(未确认迁移), 用于管理普通应用的进程

    参考 paas_wl.bk_app.deploy.app_res.controllers.ProcessesHandler 实现
    """

    def __init__(self, client: EnhancedApiClient, wl_app: WlApp):
        self.client = client
        self.wl_app = wl_app

    @classmethod
    def new_by_app(cls, wl_app: WlApp):
        """Create a controller object by wl_app object"""
        client = get_client_by_app(wl_app)
        return cls(client, wl_app)

    def get_processes_info(self) -> ProcessesInfo:
        """get processes info by wl_app"""
        processes: List[Process] = []

        procs = process_kmodel.list_by_app_with_meta(self.wl_app)
        insts = instance_kmodel.list_by_app_with_meta(self.wl_app)

        for proc in procs.items:
            proc.instances = [inst for inst in insts.items if inst.process_type == proc.type]
            processes.append(proc)

        return ProcessesInfo(
            processes=processes, rv_proc=procs.get_resource_version(), rv_inst=insts.get_resource_version()
        )

    def start(self, config: MapperProcConfig):
        """Start a process with one replica

        :param config: The mapper proc config object
        """
        self._scale(config, replicas=1)

    def stop(self, config: MapperProcConfig):
        """stop a process

        :param config: The mapper proc config object
        """
        self._scale(config, replicas=0)

    def scale(self, config: MapperProcConfig, replicas: int):
        """scale a process

        :param config: The mapper proc config object
        """
        self._scale(config, replicas)

    def _scale(self, config: MapperProcConfig, replicas: int):
        """Scale a process's replicas to given value

        :param config: The mapper proc config object
        :param replicas: The replicas value, such as 2
        """
        ProcessesHandler.get_default_services(config.app, config.type).create_or_patch()

        # Send patch request
        patch_body = {"spec": {"replicas": replicas}}
        KDeployment(self.client).patch(
            ProcessesHandler.res_identifiers(config).deployment_name, namespace=config.app.namespace, body=patch_body
        )
