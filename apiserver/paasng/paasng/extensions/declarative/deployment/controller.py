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
from typing import Dict

import cattr
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from paas_wl.platform.api import upsert_app_monitor
from paasng.engine.constants import ConfigVarEnvName
from paasng.engine.models.deployment import Deployment
from paasng.engine.models.processes import ProcessManager
from paasng.extensions.declarative.deployment.resources import BluekingMonitor, DeploymentDesc, Process
from paasng.extensions.declarative.exceptions import ControllerError
from paasng.extensions.declarative.models import DeploymentDescription

logger = logging.getLogger(__name__)


class DeploymentDeclarativeController:
    """A controller which process deployment descriptions"""

    def __init__(self, deployment: Deployment):
        self.deployment = deployment

    @atomic
    def perform_action(self, desc: DeploymentDesc):
        """Perform action by given description

        :param desc: deployment specification
        """
        logger.debug('Update related deployment description object.')
        # Save given description config into database
        DeploymentDescription.objects.update_or_create(
            deployment=self.deployment,
            defaults={
                'env_variables': desc.get_env_variables(ConfigVarEnvName(self.deployment.app_environment.environment)),
                'runtime': {
                    'processes': cattr.unstructure(desc.processes),
                    'svc_discovery': cattr.unstructure(desc.svc_discovery),
                    "source_dir": desc.source_dir,
                },
                'scripts': cattr.unstructure(desc.scripts),
                # TODO: store desc.bk_monitor to DeploymentDescription
            },
        )
        # Bind ProcessSpec if necessary
        if desc.processes:
            self.sync_processes_specs(desc.processes)
        else:
            logger.debug("The description file does not define processes, deployment pk: %s", self.deployment.pk)
        if desc.bk_monitor:
            self.update_bkmonitor(desc.bk_monitor)

    def sync_processes_specs(self, processes: Dict[str, Process]):
        """同步进程定义信息"""
        engine_app = self.deployment.get_engine_app()
        process_manager = ProcessManager(engine_app)

        try:
            process_manager.sync_processes_specs(
                [
                    {
                        "name": process_name,
                        "command": process.command,
                        "replicas": process.replicas,
                        "plan": process.plan,
                    }
                    for process_name, process in processes.items()
                ]
            )
        except Exception as e:
            raise ControllerError(_("同步进程信息时出现异常，请检查应用描述文件或联系平台管理员")) from e

    def update_bkmonitor(self, bk_monitor: BluekingMonitor):
        """更新 SaaS 监控配置"""
        engine_app = self.deployment.get_engine_app()
        upsert_app_monitor(
            engine_app_name=engine_app.name,
            port=bk_monitor.port,
            target_port=bk_monitor.target_port,  # type: ignore
        )
