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

import logging
from typing import List, Optional

from django.db.transaction import atomic

from paas_wl.bk_app.monitoring.app_monitor.shim import upsert_app_monitor
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.bkapp_model.entities import Process
from paasng.platform.bkapp_model.entities.v1alpha2 import BkAppSpec
from paasng.platform.bkapp_model.entities_syncer import sync_processes
from paasng.platform.bkapp_model.fieldmgr import FieldMgrName
from paasng.platform.bkapp_model.importer import import_bkapp_spec_entity, import_bkapp_spec_entity_non_cnative
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.resources import BluekingMonitor, DeploymentDesc, ProcfileProc
from paasng.platform.declarative.entities import DeployHandleResult
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.engine.models.deployment import Deployment, ProcessTmpl

logger = logging.getLogger(__name__)


class DeploymentDeclarativeController:
    """A controller which process deployment description, it was triggered by a
    new deployment action. The controller handle a given description which was parsed
    from the source file and do following things:

    - Get and save the processes data
    - Save other data such as env vars and svc discovery

    :param deployment: The deployment object.
    """

    def __init__(self, deployment: Deployment):
        self.deployment = deployment
        self.module = self.deployment.app_environment.module
        self.application = self.module.application

    @atomic
    def perform_action(
        self, desc: DeploymentDesc, procfile_procs: Optional[List[ProcfileProc]] = None
    ) -> DeployHandleResult:
        """Perform action by given description and procfile data.

        :param desc: The deployment specification
        :param procfile_procs: The processes list defined by the Procfile
        :raise: DescriptionValidationError: when any validation error occurs
        """
        if procfile_procs:
            try:
                desc.use_procfile_procs(procfile_procs)
            except ValueError:
                raise DescriptionValidationError(
                    "Process definitions conflict between Procfile and app description file. "
                    "Please remove the Procfile to resolve this conflict."
                )

        self.handle_desc(desc)

        return DeployHandleResult(desc.spec_version)

    def handle_desc(self, desc: DeploymentDesc):
        """Handle the description object, which was read from the app description file.

        :raise: DescriptionValidationError when non-cloud native application use app_desc.yaml of version(specVersion:3)
        """

        if self.application.type != ApplicationType.CLOUD_NATIVE and desc.spec_version == AppSpecVersion.VER_3:
            raise DescriptionValidationError(
                "Non-cloud native application do not support app_desc.yaml of version(specVersion: 3)"
            )

        if desc.bk_monitor:
            self._update_bkmonitor(desc.bk_monitor)

        desc_obj = self._save_desc_obj(desc)
        if self.application.type == ApplicationType.CLOUD_NATIVE:
            self._handle_desc_cnative_style(desc_obj.spec)
        else:
            self._handle_desc_normal_style(desc_obj.spec)

        # 总是将本次解析的进程数据保存到当前 deployment 对象中, 用于普通应用的进程配置同步(ProcessManager.sync_processes_specs)
        self.deployment.update_fields(processes=desc.get_proc_tmpls())

    def _handle_desc_cnative_style(self, spec_obj: BkAppSpec):
        """适用于：云原生应用或采用了 version 3 版本的应用描述文件"""
        import_bkapp_spec_entity(self.module, spec_entity=spec_obj, manager=FieldMgrName.APP_DESC)

    def _handle_desc_normal_style(self, spec_obj: BkAppSpec):
        """适用于：普通应用"""
        import_bkapp_spec_entity_non_cnative(self.module, spec_entity=spec_obj, manager=FieldMgrName.APP_DESC)

    def _save_desc_obj(self, desc: DeploymentDesc) -> DeploymentDescription:
        """Save the raw description data, return the object created."""
        deploy_desc, _ = DeploymentDescription.objects.update_or_create(
            deployment=self.deployment,
            defaults={
                "runtime": {"source_dir": desc.source_dir},
                "spec": desc.spec,
                "tenant_id": self.deployment.tenant_id,
                # TODO: store desc.bk_monitor to DeploymentDescription
            },
        )
        return deploy_desc

    def _update_bkmonitor(self, bk_monitor: BluekingMonitor):
        """更新 SaaS 监控配置"""
        upsert_app_monitor(
            env=self.deployment.app_environment,
            port=bk_monitor.port,
            target_port=bk_monitor.target_port,  # type: ignore
        )


def handle_procfile_procs(deployment: Deployment, procfile_procs: List[ProcfileProc]) -> DeployHandleResult:
    """Handle the processes defined by Procfile, this function only sync the process
    configs to the database model.

    :param deployment: The deployment object
    :param procfile_procs: The processes defined by Procfile
    """
    module = deployment.app_environment.module

    processes = [Process(name=p.name, proc_command=p.command) for p in procfile_procs]
    sync_processes(module, processes, FieldMgrName.APP_DESC, use_proc_command=True)

    # 更新 deployment 中的 processes, 用于普通应用的进程配置同步(ProcessManager.sync_processes_specs)
    proc_tmpls = {p.name: ProcessTmpl(name=p.name, command=p.command) for p in procfile_procs}
    deployment.update_fields(processes=proc_tmpls)

    return DeployHandleResult()
