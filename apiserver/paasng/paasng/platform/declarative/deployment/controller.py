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
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import cattr
from attrs import define, fields
from django.db.transaction import atomic

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paas_wl.bk_app.monitoring.app_monitor.shim import upsert_app_monitor
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.bkapp_model.importer import env_vars, import_manifest, svc_discovery
from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager, sync_hooks
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.process_probe import delete_process_probes, upsert_process_probe
from paasng.platform.declarative.deployment.resources import BluekingMonitor, DeploymentDesc, ProbeSet, Process
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.engine.models.deployment import Deployment, ProcessTmpl

logger = logging.getLogger(__name__)


@define
class PerformResult:
    """应用描述文件的导入结果

    :param loaded_processes: 导入的进程信息, 进程命令为 Procfile 格式.
                             如进程信息与 Procfile 中的进程冲突, 将根据应用类型作出不同的策略.
                             - 普通应用, 以 Procfile 为准
                             - 云原生应用, 以应用描述文件为准
    """

    spec_version: AppSpecVersion
    loaded_processes: Optional[Dict[str, ProcessTmpl]] = None

    def set_processes(self, processes: Dict[str, Process]):
        self.loaded_processes = cattr.structure(
            {
                proc_name: {
                    "name": proc_name,
                    "command": process.command,
                    "replicas": process.replicas,
                    "plan": process.plan,
                }
                for proc_name, process in processes.items()
            },
            Dict[str, ProcessTmpl],
        )

    def is_use_cnb(self) -> bool:
        return self.spec_version == AppSpecVersion.VER_3


def convert_bkapp_spec_to_manifest(spec: bk_app.BkAppSpec) -> Dict:
    """将应用描述文件中的 BkAppSpec 转换成适合直接导入到模型的格式"""
    # 应用描述文件中的环境变量不展示到产品页面
    exclude: Mapping[Union[str, int], Any] = {
        "configuration": ...,
        "envOverlay": {"envVariables"},
    }
    return {
        "metadata": {},
        "spec": spec.dict(exclude_none=True, exclude=exclude),
    }


def get_preset_env_vars(spec: bk_app.BkAppSpec) -> Tuple[List[bk_app.EnvVar], List[bk_app.EnvVarOverlay]]:
    """从应用描述文件中提取预定义环境变量, 存储到 PresetEnvVariable 表中"""
    overlay_env_vars: List[bk_app.EnvVarOverlay] = []
    if spec.envOverlay:
        overlay_env_vars = spec.envOverlay.envVariables or []
    return spec.configuration.env, overlay_env_vars


def get_svc_discovery(spec: bk_app.BkAppSpec) -> Optional[bk_app.SvcDiscConfig]:
    """从应用描述文件中提取服务发现配置, 存储到 SvcDiscConfig 表中

    NOTE: 仅用于普通应用, 让普通应用也可以通过 SvcDiscConfig 模型拿到服务发现配置的环境变量
    (云原生应用在 import_manifest 已导入服务发现配置)
    """
    return spec.svcDiscovery


class DeploymentDeclarativeController:
    """A controller which process deployment descriptions"""

    def __init__(self, deployment: Deployment):
        self.deployment = deployment

    @atomic
    def perform_action(self, desc: DeploymentDesc) -> PerformResult:
        """Perform action by given description

        :param desc: deployment specification
        """
        result = PerformResult(spec_version=desc.spec_version)
        logger.debug("Update related deployment description object.")

        application = self.deployment.app_environment.application
        module = self.deployment.app_environment.module
        processes = desc.get_processes()
        deploy_desc, _ = DeploymentDescription.objects.update_or_create(
            deployment=self.deployment,
            defaults={
                "runtime": {
                    "source_dir": desc.source_dir,
                },
                "spec": desc.spec,
                # TODO: store desc.bk_monitor to DeploymentDescription
            },
        )

        # apply desc to bkapp_model
        result.set_processes(processes=processes)
        if desc.spec_version == AppSpecVersion.VER_3 or application.type == ApplicationType.CLOUD_NATIVE:
            # 云原生应用
            # TODO: 优化 import 方式, 例如直接接受 desc.spec
            # Warning: app_desc 中声明的 hooks 会覆盖产品上已填写的 hooks
            # Warning: import_manifest 时, proc_command 会被置为 None, 仅 command/args 会保留
            import_manifest(
                module,
                input_data=convert_bkapp_spec_to_manifest(deploy_desc.spec),
            )
            if hooks := deploy_desc.get_deploy_hooks():
                self.deployment.update_fields(hooks=hooks)
        else:
            # 普通应用
            # Note: 由于普通应用可能在 Procfile 定义进程, 因此在应用构建时仍然存在其他位点会更新 ModuleProcessSpecManager
            # TODO: 优化如上所述的情况
            if result.loaded_processes:
                ModuleProcessSpecManager(module).sync_from_desc(processes=list(result.loaded_processes.values()))
            # 仅声明 hooks 时才同步 hooks
            # 由于普通应用仍然可以在页面上填写部署前置命令, 因此当描述文件未配置 hooks 时, 不代表禁用 hooks.
            if hooks := deploy_desc.get_deploy_hooks():
                sync_hooks(module, hooks)
                self.deployment.update_fields(hooks=hooks)
            # 导入服务发现配置
            # Warning: SvcDiscConfig 是 Application 全局的, 多模块配置不一样时会互相覆盖(这与普通应用原来的行为不一致, 但目前暂无更好的解决方案)
            if svc_disc := get_svc_discovery(spec=desc.spec):
                svc_discovery.import_svc_discovery(module=module, svc_disc=svc_disc)
        # 导入预定义环境变量
        env_vars.import_preset_env_vars(module, *get_preset_env_vars(desc.spec))

        if desc.bk_monitor:
            self.update_bkmonitor(desc.bk_monitor)

        # 为了保证 probe 对象不遗留，对 probe 进行全量删除和全量更新
        # 对该环境下的 probe 进行全量删除
        self.delete_probes()

        # 根据配置，对 probe 进行全量更新
        for process_type, process in processes.items():
            self.update_probes(process_type=process_type, probes=process.probes)

        return result

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

    def update_probes(self, process_type: str, probes: Optional[ProbeSet] = None):
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
