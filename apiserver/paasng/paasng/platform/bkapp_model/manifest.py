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
import json
import logging
import shlex
from abc import ABC, abstractmethod
from operator import itemgetter
from typing import Dict, List, Tuple

from kubernetes.utils.quantity import parse_quantity

from paas_wl.bk_app.cnative.specs.constants import (
    ACCESS_CONTROL_ANNO_KEY,
    BKPAAS_ADDONS_ANNO_KEY,
    LEGACY_PROC_IMAGE_ANNO_KEY,
    ApiVersion,
    ResQuotaPlan,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import (
    BkAppAddon,
    BkAppProcess,
    BkAppResource,
    BkAppSpec,
    EnvOverlay,
    EnvVar,
    EnvVarOverlay,
    ObjectMetadata,
)
from paas_wl.bk_app.cnative.specs.models import generate_bkapp_name
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP
from paas_wl.bk_app.processes.models import ProcessSpecPlan
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.engine.constants import AppEnvName, RuntimeType
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


# legacy: Slug runner 默认的 entrypoint, 平台所有 slug runner 镜像都以该值作为入口
DEFAULT_SLUG_RUNNER_ENTRYPOINT = ['bash', '/runner/init']


class ManifestConstructor(ABC):
    """Construct the manifest for bk_app model, it is usually only responsible for a small part of the manifest."""

    @abstractmethod
    def apply_to(self, model_res: BkAppResource, module: Module):
        """Apply current constructor to the model resource object.

        :param model_res: The bkapp model resource object.
        :param module: The application module.
        :raise ManifestConstructorError: Unable to apply current constructor due to errors.
        """
        raise NotImplementedError()


class AddonsManifestConstructor(ManifestConstructor):
    """Construct the "addons" part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        names = [svc.name for svc in mixed_service_mgr.list_binded(module)]
        # Modify both annotations and spec
        model_res.metadata.annotations[BKPAAS_ADDONS_ANNO_KEY] = json.dumps(names)
        for name in names:
            model_res.spec.addons.append(BkAppAddon(name=name))


class AccessControlManifestConstructor(ManifestConstructor):
    """Construct the access-control part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        try:
            from paasng.security.access_control.models import ApplicationAccessControlSwitch
        except ImportError:
            # The module is not enabled in current edition
            return

        if ApplicationAccessControlSwitch.objects.is_enabled(module.application):
            model_res.metadata.annotations[ACCESS_CONTROL_ANNO_KEY] = "true"


class BuiltinAnnotsManifestConstructor(ManifestConstructor):
    """Construct the built-in annotations."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        # TODO: ref to `_inject_annotations()` method
        pass


class BuildConfigManifestConstructor(ManifestConstructor):
    """Construct the build config."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        # TODO
        pass


class ProcessesManifestConstructor(ManifestConstructor):
    """Construct the processes part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        process_specs = list(ModuleProcessSpec.objects.filter(module=module).order_by("created"))
        if not process_specs:
            logger.warning("模块<%s> 未定义任何进程", module)
            return

        legacy_processes = {}
        processes = []
        for process_spec in process_specs:
            try:
                command, args = self.get_command_and_args(module, process_spec)
            except ValueError:
                logger.warning("模块<%s>的 %s 进程 未定义启动命令, 将使用镜像默认命令运行", module, process_spec.name)
                command, args = [], []
            processes.append(
                BkAppProcess(
                    name=process_spec.name,
                    replicas=process_spec.target_replicas,
                    command=command,
                    args=args,
                    targetPort=process_spec.port,
                    # TODO?: 是否需要使用 LEGACY_PROC_RES_ANNO_KEY 存储不支持的 plan
                    resQuotaPlan=self.get_quota_plan(process_spec.plan_name),
                    autoscaling=process_spec.scaling_config if process_spec.autoscaling else None,
                )
            )
            # deprecated: support v1alpha1
            if process_spec.image:
                legacy_processes[process_spec.name] = {
                    "image": process_spec.image,
                    "policy": process_spec.image_pull_policy,
                }

        if legacy_processes:
            model_res.metadata.annotations[LEGACY_PROC_IMAGE_ANNO_KEY] = json.dumps(legacy_processes)
        model_res.spec.processes = processes

    @staticmethod
    def get_quota_plan(spec_plan_name: str) -> ResQuotaPlan:
        """Get ProcessSpecPlan by name and transform it to ResQuotaPlan"""
        try:
            spec_plan = ProcessSpecPlan.objects.get_by_name(name=spec_plan_name)
        except ProcessSpecPlan.DoesNotExist:
            return ResQuotaPlan.P_DEFAULT

        # Memory 稀缺性比 CPU 要高, 转换时只关注 Memory
        limits = spec_plan.get_resource_summary()['limits']
        expected_limit_memory = parse_quantity(limits.get("memory", "512Mi"))
        quota_plan_memory = sorted(
            ((parse_quantity(limit.memory), quota_plan) for quota_plan, limit in PLAN_TO_LIMIT_QUOTA_MAP.items()),
            key=itemgetter(0),
        )
        for limit_memory, quota_plan in quota_plan_memory:
            if limit_memory >= expected_limit_memory:
                return quota_plan
        return quota_plan_memory[-1][0]

    @staticmethod
    def get_command_and_args(module: Module, process_spec: ModuleProcessSpec) -> Tuple[List[str], List[str]]:
        """Get K8s COMMAND/ARGS pair from process_spec"""
        # 仅托管镜像的应用目前会在页面上配置 command/args 字段, 其余类型的应用使用 proc_command 声明启动命令
        if process_spec.command or process_spec.args:
            return process_spec.command or [], process_spec.args or []

        mgr = ModuleRuntimeManager(module)
        if mgr.build_config.build_method == RuntimeType.BUILDPACK:
            if mgr.is_cnb_runtime:
                # cnb buildpack 启动进程时只能通过 `进程名` 来调用 Procfile 中的命令(相关命令已被 cnb buildpack 打包到镜像内)
                return [process_spec.name], []
            # 普通应用的启动命令固定了 entrypoint
            return DEFAULT_SLUG_RUNNER_ENTRYPOINT, ["start", process_spec.name]
        elif mgr.build_config.build_method == RuntimeType.DOCKERFILE:
            o = shlex.split(process_spec.proc_command)
            return [o[0]], o[1:]
        raise ValueError


class EnvVarsManifestConstructor(ManifestConstructor):
    """Construct the env variables part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        # The global variables
        for var in ConfigVar.objects.filter(module=module, environment_id=ENVIRONMENT_ID_FOR_GLOBAL).order_by('key'):
            model_res.spec.configuration.env.append(EnvVar(name=var.key, value=var.value))

        # The environment specific variables
        overlay = model_res.spec.envOverlay
        if not overlay:
            overlay = EnvOverlay()
        for env in [AppEnvName.STAG.value, AppEnvName.PROD.value]:
            for var in ConfigVar.objects.filter(module=module, environment=module.get_envs(env)).order_by('key'):
                if overlay.envVariables is None:
                    overlay.envVariables = []
                overlay.envVariables.append(EnvVarOverlay(envName=env, name=var.key, value=var.value))

        model_res.spec.envOverlay = overlay


class HooksManifestConstructor(ManifestConstructor):
    """Construct the hooks part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        # TODO
        pass


def get_manifest(module: Module) -> List[Dict]:
    """Get the manifest of current module, the result might contain multiple items."""
    return [
        get_bk_app_resource(module).to_deployable(),
    ]


def get_bk_app_resource(module: Module) -> BkAppResource:
    """Get the manifest of current module.

    :param module: The module object.
    :returns: The resource object.
    """
    builders: List[ManifestConstructor] = [
        BuiltinAnnotsManifestConstructor(),
        AddonsManifestConstructor(),
        AccessControlManifestConstructor(),
        ProcessesManifestConstructor(),
        HooksManifestConstructor(),
        BuildConfigManifestConstructor(),
        EnvVarsManifestConstructor(),
    ]
    obj = BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2,
        metadata=ObjectMetadata(name=generate_bkapp_name(module)),
        spec=BkAppSpec(),
    )
    for builder in builders:
        builder.apply_to(obj, module)
    return obj
