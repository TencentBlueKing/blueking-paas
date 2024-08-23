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
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import cattr
from attrs import define
from django.db.transaction import atomic

from paas_wl.bk_app.cnative.specs.constants import PROC_SERVICES_ENABLED_ANNOTATION_KEY
from paas_wl.bk_app.monitoring.app_monitor.shim import upsert_app_monitor
from paas_wl.bk_app.processes.constants import ProbeType
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.bkapp_model.entities import EnvVar, EnvVarOverlay, ProbeSet, Process, SvcDiscConfig, v1alpha2
from paasng.platform.bkapp_model.entities_syncer import sync_svc_discovery
from paasng.platform.bkapp_model.importer import import_bkapp_spec_entity
from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager, sync_hooks
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.process_probe import delete_process_probes, upsert_process_probe
from paasng.platform.declarative.deployment.resources import BluekingMonitor, DeploymentDesc
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.engine.configurations import preset_envvars
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
        """Set the "loaded_processes" property, basically it do a type conversion
        from Process to ProcessTmpl.
        """
        self.loaded_processes = cattr.structure(
            {
                proc_name: {
                    "name": proc_name,
                    "command": process.get_proc_command(),
                    "replicas": process.replicas,
                    "plan": process.res_quota_plan,
                    "probes": process.probes,
                }
                for proc_name, process in processes.items()
            },
            Dict[str, ProcessTmpl],
        )

    def is_use_cnb(self) -> bool:
        return self.spec_version == AppSpecVersion.VER_3


def sanitize_bkapp_spec_to_dict(spec: v1alpha2.BkAppSpec) -> Dict:
    """将应用描述文件中的 BkAppSpec 转换成适合直接导入到模型的格式"""
    # 应用描述文件中的环境变量不展示到产品页面
    exclude: Mapping[Union[str, int], Any] = {
        "configuration": ...,
        "env_overlay": {"env_variables"},
    }
    return spec.dict(exclude_none=True, exclude=exclude)


def get_preset_env_vars(spec: v1alpha2.BkAppSpec) -> Tuple[List[EnvVar], List[EnvVarOverlay]]:
    """从应用描述文件中提取预定义环境变量, 存储到 PresetEnvVariable 表中"""
    overlay_env_vars: List[EnvVarOverlay] = []
    if spec.env_overlay:
        overlay_env_vars = spec.env_overlay.env_variables or []
    return spec.configuration.env, overlay_env_vars


def get_svc_discovery(spec: v1alpha2.BkAppSpec) -> Optional[SvcDiscConfig]:
    """从应用描述文件中提取服务发现配置, 存储到 SvcDiscConfig 表中

    NOTE: 仅用于普通应用, 让普通应用也可以通过 SvcDiscConfig 模型拿到服务发现配置的环境变量
    (云原生应用在 import_manifest 已导入服务发现配置)
    """
    return spec.svc_discovery


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
        processes: Dict[str, Process] = desc.get_processes()

        runtime = {
            "source_dir": desc.source_dir,
        }
        # specVersion: 3 ，默认开启 proc services 特性; 旧版本不启用
        if desc.spec_version == AppSpecVersion.VER_3:
            runtime[PROC_SERVICES_ENABLED_ANNOTATION_KEY] = "true"
        else:
            runtime[PROC_SERVICES_ENABLED_ANNOTATION_KEY] = "false"

        deploy_desc, _ = DeploymentDescription.objects.update_or_create(
            deployment=self.deployment,
            defaults={
                "runtime": runtime,
                "spec": desc.spec,
                # TODO: store desc.bk_monitor to DeploymentDescription
            },
        )
        result.set_processes(processes=processes)
        # apply desc to bkapp_model
        if desc.spec_version == AppSpecVersion.VER_3 or application.type == ApplicationType.CLOUD_NATIVE:
            # == 云原生应用 或者 使用了 version 3 版本的应用描述文件
            #
            # TODO: 优化 import 方式, 例如直接接受 desc.spec
            # Warning: app_desc 中声明的 hooks 会覆盖产品上已填写的 hooks
            # ---
            #
            # NOTE: 对于云原生应用， import_bkapp_spec_entity() 的默认行为是将 spec 中的数据导入
            # 到平台中，所有数据以它为准，是类似 PUT 请求的全量更新行为。然后这会导致一个问题：
            #
            # - 用户只在描述文件中定义了进程，未通过 envOverlay 定义区分环境的 replicas 数据
            # - 用户通过产品页面，对进程进行了扩缩容，数据记录在 ProcessSpecEnvOverlay 中（体现为
            #   模型中的 envOverlay）
            # - 用户重新部署，import_bkapp_spec_entity() 将描述文件中的数据导入，其判断没有 envOverlay
            #   数据，已有的 ProcessSpecEnvOverlay 数据被删除，用户设置的副本数丢失
            #
            # 为了解决这个问题，我们在 import_bkapp_spec_entity() 中增加了 reset_overlays_when_absent 参数，
            # 比在这里调用时，将其设置为 False，避免已有的 envOverlay 数据被删除。
            #
            # 然而，这也算不上是万全之策。因为用户仍然可能会在描述文件中定义 envOverlay 数据，
            # 或删除已有的 envOverlay 数据，这些操作仍然可能会导致预期之外的后果。更彻底的解决
            # 方法，可能包括以下方面：
            #
            # - 在 ProcessSpecEnvOverlay 等数据模型中增加字段（或增加新模型），以区分由
            #   用户手动设置的数据和由描述文件导入的数据，并依据一定优先级来处理
            # - 模仿和参考 kubectl apply 的行为，开发新方法 apply_manifest()，对于通过
            #   由配置文件定义的内容（比如 ProcessSpecEnvOverlay），打上特定的 manage-by
            #   标签，这样，当配置文件中没有定义时，仅在旧数据原本是由配置文件定义时才删除，
            #   否则跳过。
            #
            import_bkapp_spec_entity(
                module,
                spec_entity=v1alpha2.BkAppSpec(**sanitize_bkapp_spec_to_dict(deploy_desc.spec)),
                # Don't remove existed overlays data when no overlays data in input_data
                reset_overlays_when_absent=False,
            )
            if hooks := deploy_desc.get_deploy_hooks():
                self.deployment.update_fields(hooks=hooks)
        else:
            # == 普通应用
            #
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
                sync_svc_discovery(module=module, svc_disc=svc_disc)

            # 为了保证 probe 对象不遗留，对 probe 进行全量删除和全量更新
            # 对该环境下的 probe 进行全量删除
            self.delete_probes()

            # 根据配置，对 probe 进行全量更新
            for process_type, process in processes.items():
                self.update_probes(process_type=process_type, probes=process.probes)

        preset_envvars.batch_save(module, *get_preset_env_vars(desc.spec))

        if desc.bk_monitor:
            self.update_bkmonitor(desc.bk_monitor)

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

        for probe, p_type in [
            (probes.liveness, ProbeType.LIVENESS),
            (probes.readiness, ProbeType.READINESS),
            (probes.startup, ProbeType.STARTUP),
        ]:
            if probe:
                upsert_process_probe(
                    env=self.deployment.app_environment,
                    process_type=process_type,
                    probe_type=p_type,
                    probe=probe,
                )
