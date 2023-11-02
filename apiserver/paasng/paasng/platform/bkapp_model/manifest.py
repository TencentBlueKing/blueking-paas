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
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from kubernetes.utils.quantity import parse_quantity

from paas_wl.bk_app.applications.models.managers.app_metadata import get_metadata
from paas_wl.bk_app.cnative.specs.constants import (
    ACCESS_CONTROL_ANNO_KEY,
    BKAPP_CODE_ANNO_KEY,
    BKAPP_NAME_ANNO_KEY,
    BKAPP_REGION_ANNO_KEY,
    BKPAAS_ADDONS_ANNO_KEY,
    BKPAAS_DEPLOY_ID_ANNO_KEY,
    ENVIRONMENT_ANNO_KEY,
    IMAGE_CREDENTIALS_REF_ANNO_KEY,
    LEGACY_PROC_IMAGE_ANNO_KEY,
    MODULE_NAME_ANNO_KEY,
    PA_SITE_ID_ANNO_KEY,
    USE_CNB_ANNO_KEY,
    WLAPP_NAME_ANNO_KEY,
    ApiVersion,
    MountEnvName,
    ResQuotaPlan,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import (
    AutoscalingOverlay,
    BkAppAddon,
    BkAppBuildConfig,
    BkAppHooks,
    BkAppProcess,
    BkAppResource,
    BkAppSpec,
    EnvOverlay,
    EnvVar,
    EnvVarOverlay,
    Hook,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import Mount as MountSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import MountOverlay, ObjectMetadata, ReplicasOverlay, ResQuotaOverlay
from paas_wl.bk_app.cnative.specs.models import Mount, generate_bkapp_name
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP
from paas_wl.bk_app.processes.models import ProcessSpecPlan
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.bkapp_model.utils import merge_env_vars
from paasng.platform.engine.configurations.config_var import get_builtin_env_variables
from paasng.platform.engine.constants import AppEnvName, RuntimeType
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.models import BuildConfig, Module

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
        # Application basic info
        application = module.application
        model_res.metadata.annotations.update(
            {
                BKAPP_REGION_ANNO_KEY: application.region,
                BKAPP_NAME_ANNO_KEY: application.name,
                BKAPP_CODE_ANNO_KEY: application.code,
                MODULE_NAME_ANNO_KEY: module.name,
            }
        )
        # Set the annotation to inform operator that the secret has been created.
        model_res.metadata.annotations[IMAGE_CREDENTIALS_REF_ANNO_KEY] = "true"

        # 采用 CNB 的应用在启动进程时，entrypoint 为 `process_type`, command 是空列表，
        # 执行其他命令需要用 `launcher` 进入 buildpack 上下文，因此需要特殊标注
        # See: https://github.com/buildpacks/lifecycle/blob/main/cmd/launcher/cli/launcher.go
        model_res.metadata.annotations[USE_CNB_ANNO_KEY] = (
            "true" if ModuleRuntimeManager(module).is_cnb_runtime else "false"
        )


class BuildConfigManifestConstructor(ManifestConstructor):
    """Construct the build config."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        cfg = BuildConfig.objects.get_or_create_by_module(module)
        build = model_res.spec.build
        if not build:
            build = BkAppBuildConfig()
        if cfg.build_method == RuntimeType.CUSTOM_IMAGE:
            build.imageCredentialsName = cfg.image_credential_name
        model_res.spec.build = build


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

        # Apply other env-overlay related changes.
        self.apply_to_proc_overlay(model_res, module)

    def apply_to_proc_overlay(self, model_res: BkAppResource, module: Module):
        """Apply changes to the sub-fields in the 'envOverlay' field which is related
        with process, fields list:

        - replicas
        - autoscaling
        - resQuotas
        """
        overlay = model_res.spec.envOverlay
        if not overlay:
            overlay = EnvOverlay()

        for proc_spec in ModuleProcessSpec.objects.filter(module=module).order_by("created"):
            for item in ProcessSpecEnvOverlay.objects.filter(proc_spec=proc_spec):
                # Only include item that have different values
                if item.target_replicas is not None and item.target_replicas != proc_spec.target_replicas:
                    overlay.append_item(
                        'replicas',
                        ReplicasOverlay(
                            envName=item.environment_name, process=proc_spec.name, count=item.target_replicas
                        ),
                    )
                if item.scaling_config and item.autoscaling and item.scaling_config != proc_spec.scaling_config:
                    overlay.append_item(
                        'autoscaling',
                        AutoscalingOverlay(
                            envName=item.environment_name, process=proc_spec.name, **item.scaling_config
                        ),
                    )
                if item.plan_name and item.plan_name != proc_spec.plan_name:
                    overlay.append_item(
                        'resQuotas',
                        ResQuotaOverlay(
                            envName=item.environment_name,
                            process=proc_spec.name,
                            plan=self.get_quota_plan(item.plan_name),
                        ),
                    )

        model_res.spec.envOverlay = overlay

    @staticmethod
    def get_quota_plan(spec_plan_name: str) -> ResQuotaPlan:
        """Get ProcessSpecPlan by name and transform it to ResQuotaPlan"""
        try:
            return ResQuotaPlan(spec_plan_name)
        except ValueError:
            logger.debug(
                "unknown ResQuotaPlan value `%s`, try to convert ProcessSpecPlan to ResQuotaPlan", spec_plan_name
            )

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
        return quota_plan_memory[-1][1]

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
                overlay.append_item('envVariables', EnvVarOverlay(envName=env, name=var.key, value=var.value))

        model_res.spec.envOverlay = overlay


class HooksManifestConstructor(ManifestConstructor):
    """Construct the hooks part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        hooks = model_res.spec.hooks
        if not hooks:
            hooks = BkAppHooks()
        pre_release_hook = module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        if pre_release_hook and pre_release_hook.enabled:
            hooks.preRelease = Hook(
                command=pre_release_hook.get_command(),
                args=pre_release_hook.get_args(),
            )
        model_res.spec.hooks = hooks


class MountsManifestConstructor(ManifestConstructor):
    """Construct the mounts part."""

    def apply_to(self, model_res: BkAppResource, module: Module):
        model_res.spec.mounts = model_res.spec.mounts or []
        # The global mounts
        for config in Mount.objects.filter(module_id=module.pk, environment_name=MountEnvName.GLOBAL.value):
            model_res.spec.mounts.append(
                MountSpec(name=config.name, mountPath=config.mount_path, source=config.source_config)
            )

        # The environment specific mounts
        overlay = model_res.spec.envOverlay
        if not overlay:
            overlay = EnvOverlay()
        for env in [AppEnvName.STAG.value, AppEnvName.PROD.value]:
            for config in Mount.objects.filter(module_id=module.pk, environment_name=env):
                overlay.append_item(
                    'mounts',
                    MountOverlay(
                        envName=env, name=config.name, mountPath=config.mount_path, source=config.source_config
                    ),
                )

        model_res.spec.envOverlay = overlay


def get_manifest(module: Module) -> List[Dict]:
    """Get the manifest of current module, the result might contain multiple items."""
    return [
        get_bkapp_resource(module).to_deployable(),
    ]


def get_bkapp_resource(module: Module) -> BkAppResource:
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
        MountsManifestConstructor(),
    ]
    obj = BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2,
        metadata=ObjectMetadata(name=generate_bkapp_name(module)),
        spec=BkAppSpec(),
    )
    for builder in builders:
        builder.apply_to(obj, module)
    return obj


def get_bkapp_resource_for_deploy(
    env: ModuleEnvironment, deploy_id: str, force_image: Optional[str] = None
) -> BkAppResource:
    """Get the BkApp manifest for deploy.

    :param env: The environment object.
    :param deploy_id: The ID of the AppModelDeploy object.
    :param force_image: If given, set the image of the application to this value.
    :returns: The BkApp resource that is ready for deploying.
    """
    model_res = get_bkapp_resource(env.module)

    if force_image:
        if not model_res.spec.build:
            model_res.spec.build = BkAppBuildConfig()
        model_res.spec.build.image = force_image

    # Apply other changes to the resource
    apply_env_annots(model_res, env, deploy_id=deploy_id)
    apply_builtin_env_vars(model_res, env)

    # TODO: Missing parts: "build", "hooks", "service-disc"
    return model_res


def apply_env_annots(model_res: BkAppResource, env: ModuleEnvironment, deploy_id: Optional[str] = None):
    """Apply environment-specified annotations to the resource object.

    :param model_res: The model resource object, it will be modified in-place.
    :param env: The environment object.
    :param deploy_id: The ID of the deployment object.
    """
    wl_app = env.wl_app
    # Add environment–specific data
    model_res.metadata.annotations[ENVIRONMENT_ANNO_KEY] = env.environment
    model_res.metadata.annotations[WLAPP_NAME_ANNO_KEY] = wl_app.name
    if deploy_id is not None:
        model_res.metadata.annotations[BKPAAS_DEPLOY_ID_ANNO_KEY] = str(deploy_id)

    # Add PaaS-Analysis related values when the module has been enabled
    if bkpa_site_id := get_metadata(wl_app).bkpa_site_id:
        model_res.metadata.annotations[PA_SITE_ID_ANNO_KEY] = str(bkpa_site_id)


def apply_builtin_env_vars(model_res: BkAppResource, env: ModuleEnvironment):
    """Apply the builtin environment vars to the resource object. These vars are hidden from
    the default manifest view and should only be used in the deploying procedure.

    :param model_res: The model resource object, it will be modified in-place.
    :param env: The environment object.
    """
    env_vars = [EnvVar(name="PORT", value=str(settings.CONTAINER_PORT))]
    for name, value in get_builtin_env_variables(env.engine_app, settings.CONFIGVAR_SYSTEM_PREFIX).items():
        env_vars.append(EnvVar(name=name, value=value))

    # Merge the variables, the builtin env vars will override the existed ones
    model_res.spec.configuration.env = merge_env_vars(model_res.spec.configuration.env, env_vars)
