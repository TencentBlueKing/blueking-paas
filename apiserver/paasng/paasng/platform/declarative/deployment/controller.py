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

from django.db.transaction import atomic

from paas_wl.bk_app.cnative.specs.constants import PROC_SERVICES_ENABLED_ANNOTATION_KEY
from paas_wl.bk_app.monitoring.app_monitor.shim import upsert_app_monitor
from paas_wl.bk_app.processes.constants import ProbeType
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.bkapp_model.entities import EnvVar, EnvVarOverlay, Process, SvcDiscConfig, v1alpha2
from paasng.platform.bkapp_model.entities_syncer import sync_svc_discovery
from paasng.platform.bkapp_model.importer import import_bkapp_spec_entity
from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager, sync_hooks
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.process_probe import delete_process_probes, upsert_process_probe
from paasng.platform.declarative.deployment.resources import BluekingMonitor, DeploymentDesc, ProcfileProc
from paasng.platform.declarative.entities import DeployHandleResult
from paasng.platform.declarative.models import DeploymentDescription
from paasng.platform.engine.configurations import preset_envvars
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
        """
        if procfile_procs:
            desc.use_procfile_procs_if_conflict(procfile_procs)

        self.handle_desc(desc)

        return DeployHandleResult(use_cnb=desc.spec_version == AppSpecVersion.VER_3)

    def handle_desc(self, desc: DeploymentDesc):
        """Handle the description object, which was read from the app description file."""
        # Save the environment variables as "preset vars"
        preset_envvars.batch_save(self.module, *get_preset_env_vars(desc.spec))
        if desc.bk_monitor:
            self._update_bkmonitor(desc.bk_monitor)

        desc_obj = self._save_desc_obj(desc)
        if self._favor_cnative_style(desc):
            self._handle_desc_cnative_style(desc, desc_obj)
        else:
            self._handle_desc_normal_style(desc, desc_obj)

        # 总是将本次解析的进程数据保存到当前 deployment 对象中
        self.deployment.update_fields(processes=desc.get_proc_tmpls())

    def _handle_desc_cnative_style(self, desc: DeploymentDesc, desc_obj: DeploymentDescription):
        """
        == 云原生应用 或者 使用了 version 3 版本的应用描述文件

        TODO: 优化 import 方式, 例如直接接受 desc.spec
        Warning: app_desc 中声明的 hooks 会覆盖产品上已填写的 hooks
        ---

        NOTE: 对于云原生应用， import_bkapp_spec_entity() 的默认行为是将 spec 中的数据导入
        到平台中，所有数据以它为准，是类似 PUT 请求的全量更新行为。然后这会导致一个问题：

        - 用户只在描述文件中定义了进程，未通过 envOverlay 定义区分环境的 replicas 数据
        - 用户通过产品页面，对进程进行了扩缩容，数据记录在 ProcessSpecEnvOverlay 中（体现为
          模型中的 envOverlay）
        - 用户重新部署，import_bkapp_spec_entity() 将描述文件中的数据导入，其判断没有 envOverlay
          数据，已有的 ProcessSpecEnvOverlay 数据被删除，用户设置的副本数丢失

        为了解决这个问题，我们在 import_bkapp_spec_entity() 中增加了 reset_overlays_when_absent 参数，
        比在这里调用时，将其设置为 False，避免已有的 envOverlay 数据被删除。

        然而，这也算不上是万全之策。因为用户仍然可能会在描述文件中定义 envOverlay 数据，
        或删除已有的 envOverlay 数据，这些操作仍然可能会导致预期之外的后果。更彻底的解决
        方法，可能包括以下方面：

        - 在 ProcessSpecEnvOverlay 等数据模型中增加字段（或增加新模型），以区分由
          用户手动设置的数据和由描述文件导入的数据，并依据一定优先级来处理
        - 模仿和参考 kubectl apply 的行为，开发新方法 apply_manifest()，对于通过
          由配置文件定义的内容（比如 ProcessSpecEnvOverlay），打上特定的 manage-by
          标签，这样，当配置文件中没有定义时，仅在旧数据原本是由配置文件定义时才删除，
          否则跳过。
        """
        import_bkapp_spec_entity(
            self.module,
            spec_entity=v1alpha2.BkAppSpec(**sanitize_bkapp_spec_to_dict(desc_obj.spec)),
            # Don't remove existed overlays data when no overlays data in input_data
            reset_overlays_when_absent=False,
        )
        if hooks := desc_obj.get_deploy_hooks():
            self.deployment.update_fields(hooks=hooks)

    def _handle_desc_normal_style(self, desc: DeploymentDesc, desc_obj: DeploymentDescription):
        # # == 普通应用
        #
        # 同步进程配置
        proc_tmpls = list(desc.get_proc_tmpls().values())
        ModuleProcessSpecManager(self.module).sync_from_desc(processes=proc_tmpls)

        # 仅声明 hooks 时才同步 hooks
        # 由于普通应用仍然可以在页面上填写部署前置命令, 因此当描述文件未配置 hooks 时, 不代表禁用 hooks.
        if hooks := desc_obj.get_deploy_hooks():
            sync_hooks(self.module, hooks)
            self.deployment.update_fields(hooks=hooks)

        # 导入服务发现配置
        # Warning: SvcDiscConfig 是 Application 全局的, 多模块配置不一样时会互相覆盖(这与普通应用原来的行为不一致, 但目前暂无更好的解决方案)
        if svc_disc := get_svc_discovery(spec=desc.spec):
            sync_svc_discovery(module=self.module, svc_disc=svc_disc)

        # 更新进程探针配置
        self._update_probes(desc.get_processes())

    def _save_desc_obj(self, desc: DeploymentDesc) -> DeploymentDescription:
        """Save the raw description data, return the object created."""
        runtime = {"source_dir": desc.source_dir}

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
        return deploy_desc

    def _update_bkmonitor(self, bk_monitor: BluekingMonitor):
        """更新 SaaS 监控配置"""
        upsert_app_monitor(
            env=self.deployment.app_environment,
            port=bk_monitor.port,
            target_port=bk_monitor.target_port,  # type: ignore
        )

    def _update_probes(self, processes: Dict[str, Process]):
        """更新 SaaS 探针配置"""
        # 为了保证 probe 对象不遗留，对 probe 进行全量删除和全量更新
        # 对该环境下的 probe 进行全量删除
        delete_process_probes(env=self.deployment.app_environment)

        # 根据配置，对 probe 进行全量更新
        for process_type, process in processes.items():
            probes = process.probes
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

    def _favor_cnative_style(self, desc: DeploymentDesc) -> bool:
        """Check if current deployment should favor cnative style to handle the
        description object.
        """
        return desc.spec_version == AppSpecVersion.VER_3 or self.application.type == ApplicationType.CLOUD_NATIVE


def handle_procfile_procs(deployment: Deployment, procfile_procs: List[ProcfileProc]) -> DeployHandleResult:
    """Handle the processes defined by Procfile, this function only sync the process
    configs to the database model.

    :param deployment: The deployment object
    :param procfile_procs: The processes defined by Procfile
    """
    module = deployment.app_environment.module
    proc_tmpls = {p.name: ProcessTmpl(name=p.name, command=p.command) for p in procfile_procs}
    # Save the process configs to both the module's spec and current deployment object.
    ModuleProcessSpecManager(module).sync_from_desc(processes=list(proc_tmpls.values()))
    deployment.update_fields(processes=proc_tmpls)
    return DeployHandleResult(use_cnb=False)


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
