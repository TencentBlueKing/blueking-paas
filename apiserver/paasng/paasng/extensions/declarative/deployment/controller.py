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
from typing import Optional

import cattr
from attrs import fields
from django.db.transaction import atomic

from paas_wl.monitoring.app_monitor.shim import upsert_app_monitor
from paasng.engine.constants import ConfigVarEnvName
from paasng.engine.models.deployment import Deployment
from paasng.extensions.declarative.deployment.process_probe_handler import delete_process_probes, upsert_process_probe
from paasng.extensions.declarative.deployment.resources import BluekingMonitor, DeploymentDesc, ProbeSet
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
                    # TODO: Only save desc.processes into DeploymentDescription
                    # The synchronization of processes_spec should be delayed until the RELEASE stage
                    'processes': cattr.unstructure(desc.processes),
                    'svc_discovery': cattr.unstructure(desc.svc_discovery),
                    "source_dir": desc.source_dir,
                },
                'scripts': cattr.unstructure(desc.scripts),
                # TODO: store desc.bk_monitor to DeploymentDescription
            },
        )
        if desc.bk_monitor:
            self.update_bkmonitor(desc.bk_monitor)

        # 为了保证 probe 对象不遗留，对 probe 进行全量删除和全量更新
        # 对该环境下的 probe 进行全量删除
        self.delete_probes()

        # 根据配置，对 probe 进行全量更新
        for process_type, process in desc.processes.items():
            self.updata_probes(process_type=process_type, probes=process.probes)

    def update_bkmonitor(self, bk_monitor: BluekingMonitor):
        """更新 SaaS 监控配置"""
        upsert_app_monitor(
            env=self.deployment.app_environment,
            port=bk_monitor.port,
            target_port=bk_monitor.target_port,  # type: ignore
        )

    def delete_probes(self):
        """删除 SaaS 探针配置"""
        delete_process_probes(
            env=self.deployment.app_environment,
        )

    def updata_probes(self, process_type: str, probes: Optional[ProbeSet] = None):
        """更新 SaaS 探针配置"""
        if not probes:
            return

        for probe_field in fields(ProbeSet):
            probe = getattr(probes, probe_field.name)
            if probe:
                upsert_process_probe(
                    env=self.deployment.app_environment,
                    process_type=process_type,
                    probe_type=probe_field.name,
                    probe=probe,
                )
