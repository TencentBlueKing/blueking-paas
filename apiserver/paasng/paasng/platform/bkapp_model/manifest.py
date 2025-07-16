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
import shlex
from abc import ABC, abstractmethod
from operator import itemgetter
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from kubernetes.utils.quantity import parse_quantity

from paas_wl.bk_app.applications.managers import get_metadata
from paas_wl.bk_app.applications.models.build import Build as WlBuild
from paas_wl.bk_app.cnative.specs.constants import (
    ACCESS_CONTROL_ANNO_KEY,
    BKAPP_CODE_ANNO_KEY,
    BKAPP_NAME_ANNO_KEY,
    BKAPP_REGION_ANNO_KEY,
    BKAPP_TENANT_ID_ANNO_KEY,
    BKPAAS_DEPLOY_ID_ANNO_KEY,
    EGRESS_CLUSTER_STATE_NAME_ANNO_KEY,
    ENVIRONMENT_ANNO_KEY,
    IMAGE_CREDENTIALS_REF_ANNO_KEY,
    LAST_DEPLOY_STATUS_ANNO_KEY,
    LOG_COLLECTOR_TYPE_ANNO_KEY,
    MODULE_NAME_ANNO_KEY,
    PA_SITE_ID_ANNO_KEY,
    TENANT_GUARD_ANNO_KEY,
    WLAPP_NAME_ANNO_KEY,
    ApiVersion,
    MountEnvName,
)
from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.cnative.specs.crd.bk_app import SecretSource, VolumeSource
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.bk_app.cnative.specs.models import Mount
from paas_wl.bk_app.cnative.specs.procs.quota import PLAN_TO_LIMIT_QUOTA_MAP
from paas_wl.bk_app.processes.models import ProcessSpecPlan
from paas_wl.core.resource import generate_bkapp_name
from paas_wl.workloads.networking.egress.models import RCStateAppBinding
from paasng.accessories.log.shim import get_log_collector_type
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.sharing import ServiceSharingManager
from paasng.accessories.servicehub.tls import list_provisioned_tls_enabled_rels
from paasng.accessories.services.utils import gen_addons_cert_mount_dir, gen_addons_cert_secret_name
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model.constants import PORT_PLACEHOLDER, ResQuotaPlan
from paasng.platform.bkapp_model.entities import Process
from paasng.platform.bkapp_model.models import (
    DomainResolution,
    ModuleProcessSpec,
    ObservabilityConfig,
    ProcessSpecEnvOverlay,
    SvcDiscConfig,
)
from paasng.platform.bkapp_model.utils import (
    MergeStrategy,
    merge_env_vars,
    merge_env_vars_overlay,
    override_env_vars_overlay,
)
from paasng.platform.engine.configurations.config_var import EnvVarSource, UnifiedEnvVarsReader
from paasng.platform.engine.constants import AppEnvName, ConfigVarEnvName, RuntimeType
from paasng.platform.engine.models import Deployment
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.platform.modules.constants import DeployHookType
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.models import BuildConfig, Module
from paasng.utils.camel_converter import dict_to_camel

logger = logging.getLogger(__name__)


class ManifestConstructor(ABC):
    """Construct the manifest for bk_app model, it is usually only responsible for a small part of the manifest."""

    @abstractmethod
    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        """Apply current constructor to the model resource object.

        :param model_res: The bkapp model resource object.
        :param module: The application module.
        :raise ManifestConstructorError: Unable to apply current constructor due to errors.
        """
        raise NotImplementedError()


class AddonsManifestConstructor(ManifestConstructor):
    """Construct the "addons" part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        annot_names = []

        # TODO: Add specs support
        # Process bound services
        for svc in mixed_service_mgr.list_binded(module):
            annot_names.append(svc.name)
            model_res.spec.addons.append(crd.BkAppAddon(name=svc.name))

        # Process shared services
        for info in ServiceSharingManager(module).list_all_shared_info():
            annot_names.append(info.service.name)
            model_res.spec.addons.append(crd.BkAppAddon(name=info.service.name, sharedFromModule=info.ref_module.name))


class AccessControlManifestConstructor(ManifestConstructor):
    """Construct the access-control part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        try:
            from paasng.security.access_control.models import ApplicationAccessControlSwitch
        except ImportError:
            # The module is not enabled in current edition
            return

        if ApplicationAccessControlSwitch.objects.is_enabled(module.application):
            model_res.metadata.annotations[ACCESS_CONTROL_ANNO_KEY] = "true"


class TenantGuardManifestConstructor(ManifestConstructor):
    """Construct the tenant-guard part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        model_res.metadata.annotations[TENANT_GUARD_ANNO_KEY] = (
            "true" if settings.ENABLE_MULTI_TENANT_MODE else "false"
        )


class BuiltinAnnotsManifestConstructor(ManifestConstructor):
    """Construct the built-in annotations."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        # Application basic info
        application = module.application
        model_res.metadata.annotations.update(
            {
                BKAPP_REGION_ANNO_KEY: application.region,
                BKAPP_NAME_ANNO_KEY: application.name,
                BKAPP_CODE_ANNO_KEY: application.code,
                MODULE_NAME_ANNO_KEY: module.name,
                BKAPP_TENANT_ID_ANNO_KEY: application.app_tenant_id,
            }
        )

        # Set the annotation to inform operator what the image pull secret name is
        model_res.metadata.annotations[IMAGE_CREDENTIALS_REF_ANNO_KEY] = (
            f"{generate_bkapp_name(module)}--dockerconfigjson"
        )


class BuildConfigManifestConstructor(ManifestConstructor):
    """Construct the build config."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        cfg = BuildConfig.objects.get_or_create_by_module(module)
        build = model_res.spec.build
        if not build:
            build = crd.BkAppBuildConfig()
        if cfg.build_method == RuntimeType.CUSTOM_IMAGE:
            build.imageCredentialsName = cfg.image_credential_name
        model_res.spec.build = build


class ProcessesManifestConstructor(ManifestConstructor):
    """Construct the processes part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        process_specs = list(ModuleProcessSpec.objects.filter(module=module).order_by("created"))
        if not process_specs:
            logger.warning("模块<%s> 未定义任何进程", module)
            return

        processes = []
        for process_spec in process_specs:
            try:
                command, args = self.get_command_and_args(process_spec)
            except ValueError:
                logger.warning("模块<%s>的 %s 进程未定义启动命令, 将使用镜像默认命令运行", module, process_spec.name)
                command, args = [], []

            process_entity = Process(
                name=process_spec.name,
                command=command,
                args=args,
                replicas=process_spec.target_replicas,
                target_port=process_spec.port,
                # TODO?: 是否需要使用注解 bkapp.paas.bk.tencent.com/legacy-proc-res-config 存储不支持的 plan
                res_quota_plan=self.get_quota_plan(process_spec.plan_name),
                autoscaling=process_spec.scaling_config,
                probes=process_spec.probes.render_port() if process_spec.probes else None,
                services=([svc.render_port() for svc in process_spec.services] if process_spec.services else None),
                components=process_spec.components,
            )
            processes.append(crd.BkAppProcess(**dict_to_camel(process_entity.dict())))

        model_res.spec.processes = processes

        # Apply other env-overlay related changes.
        self.apply_to_proc_overlay(model_res, module)

    def apply_to_proc_overlay(self, model_res: crd.BkAppResource, module: Module):
        """Apply changes to the sub-fields in the 'envOverlay' field which is related
        with process, fields list:

        - replicas
        - autoscaling
        - resQuotas
        """
        overlay = model_res.spec.envOverlay
        if not overlay:
            overlay = crd.EnvOverlay()

        for proc_spec in ModuleProcessSpec.objects.filter(module=module).order_by("created"):
            for item in ProcessSpecEnvOverlay.objects.filter(proc_spec=proc_spec):
                # Only include item that have different values
                if item.target_replicas is not None and item.target_replicas != proc_spec.target_replicas:
                    overlay.append_item(
                        "replicas",
                        crd.ReplicasOverlay(
                            envName=item.environment_name, process=proc_spec.name, count=item.target_replicas
                        ),
                    )
                if item.scaling_config and item.autoscaling and item.scaling_config != proc_spec.scaling_config:
                    overlay.append_item(
                        "autoscaling",
                        crd.AutoscalingOverlay(
                            envName=item.environment_name,
                            process=proc_spec.name,
                            minReplicas=item.scaling_config.min_replicas,
                            maxReplicas=item.scaling_config.max_replicas,
                            policy=item.scaling_config.policy,
                        ),
                    )
                if item.plan_name and item.plan_name != proc_spec.plan_name:
                    overlay.append_item(
                        "resQuotas",
                        crd.ResQuotaOverlay(
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
        limits = spec_plan.get_resource_summary()["limits"]
        expected_limit_memory = parse_quantity(limits.get("memory", "512Mi"))
        quota_plan_memory = sorted(
            ((parse_quantity(limit.memory), quota_plan) for quota_plan, limit in PLAN_TO_LIMIT_QUOTA_MAP.items()),
            key=itemgetter(0),
        )
        for limit_memory, quota_plan in quota_plan_memory:
            if limit_memory >= expected_limit_memory:
                return ResQuotaPlan(quota_plan)
        # quota_plan_memory[-1][1] 是内存最大 plan
        return ResQuotaPlan(quota_plan_memory[-1][1])

    def get_command_and_args(self, process_spec: ModuleProcessSpec) -> Tuple[List[str], List[str]]:
        """Get the command and args from the process_spec object.

        :return: (command, args)
        """
        if process_spec.proc_command:
            o = self._sanitize_args(shlex.split(process_spec.proc_command))
            return [o[0]], o[1:]

        if process_spec.command or process_spec.args:
            return self._sanitize_args(process_spec.command or []), self._sanitize_args(process_spec.args or [])

        raise ValueError("Error getting command and args")

    def _sanitize_args(self, input: List[str]) -> List[str]:
        """Sanitize the command and arg list, replace some special expressions which can't
        be interpreted by the operator.
        """
        # '${PORT:-5000}' is massively used by the app framework, while it can not be used
        # in the spec directly, replace it with normal env var expression.
        return [s.replace("${PORT:-5000}", PORT_PLACEHOLDER) for s in input]


class EnvVarsManifestConstructor(ManifestConstructor):
    """Construct the env variables part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        g_preset_vars = [
            crd.EnvVar(name=var.key, value=var.value, environment_name=ConfigVarEnvName.GLOBAL)
            for var in PresetEnvVariable.objects.filter(
                module=module, environment_name=ConfigVarEnvName.GLOBAL
            ).order_by("key")
        ]
        g_user_vars = [
            crd.EnvVar(name=var.key, value=var.value)
            for var in ConfigVar.objects.filter(module=module, environment_id=ENVIRONMENT_ID_FOR_GLOBAL).order_by(
                "key"
            )
        ]
        model_res.spec.configuration.env = merge_env_vars(g_preset_vars, g_user_vars, strategy=MergeStrategy.OVERRIDE)

        # The environment specific variables
        overlay = model_res.spec.envOverlay
        if not overlay:
            overlay = model_res.spec.envOverlay = crd.EnvOverlay()
        scoped_preset_vars = [
            crd.EnvVarOverlay(envName=var.environment_name, name=var.key, value=var.value)
            for var in PresetEnvVariable.objects.filter(module=module)
            .exclude(environment_name=ConfigVarEnvName.GLOBAL)
            .order_by("key")
        ]
        scoped_user_vars = [
            crd.EnvVarOverlay(envName=var.environment.environment, name=var.key, value=var.value)
            for var in ConfigVar.objects.filter(module=module)
            .exclude(is_global=True)
            .order_by("environment__environment", "key")
        ]
        overlay.envVariables = merge_env_vars_overlay(
            scoped_preset_vars, scoped_user_vars, strategy=MergeStrategy.OVERRIDE
        )


class HooksManifestConstructor(ManifestConstructor):
    """Construct the hooks part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        hooks = model_res.spec.hooks
        if not hooks:
            hooks = crd.BkAppHooks()
        pre_release_hook = module.deploy_hooks.get_by_type(DeployHookType.PRE_RELEASE_HOOK)
        if pre_release_hook and pre_release_hook.enabled:
            hooks.preRelease = crd.Hook(
                command=pre_release_hook.get_command(),
                args=pre_release_hook.get_args(),
            )
        model_res.spec.hooks = hooks


class MountsManifestConstructor(ManifestConstructor):
    """Construct the mounts part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        # 初始化，确保数据类型符合预期
        model_res.spec.mounts = model_res.spec.mounts or []
        model_res.spec.envOverlay = model_res.spec.envOverlay or crd.EnvOverlay()
        # 增强服务 TLS 证书
        self._apply_addons_tls_certs(model_res, module)
        # 用户自定义的挂载卷
        self._apply_mounts(model_res, module)

    def _apply_addons_tls_certs(self, model_res: crd.BkAppResource, module: Module):
        """将增强服务的 TLS 证书添加到 bkapp 定义中"""
        for env in module.envs.all():
            for rel in list_provisioned_tls_enabled_rels(env):
                svc_inst = rel.get_instance()
                provider_name = svc_inst.config["provider_name"]

                secret_name = gen_addons_cert_secret_name(provider_name)
                model_res.spec.envOverlay.append_item(  # type: ignore
                    "mounts",
                    crd.MountOverlay(
                        envName=env.environment,
                        # 挂载卷名称
                        name=secret_name,
                        # 挂载路径
                        mountPath=gen_addons_cert_mount_dir(provider_name),
                        # 引用的 Secret 信息
                        source=VolumeSource(secret=SecretSource(name=secret_name)),
                    ),
                )

    def _apply_mounts(self, model_res: crd.BkAppResource, module: Module):
        """将用户自定义的挂载卷添加到 bkapp 定义中"""
        # The global mounts
        for config in Mount.objects.filter(module_id=module.pk, environment_name=MountEnvName.GLOBAL.value):
            model_res.spec.mounts.append(  # type: ignore
                crd.Mount(
                    name=config.name,
                    mountPath=config.mount_path,
                    source=config.source_config,
                    subPaths=config.sub_paths,
                )
            )

        for env in [AppEnvName.STAG, AppEnvName.PROD]:
            for config in Mount.objects.filter(module_id=module.pk, environment_name=env):
                model_res.spec.envOverlay.append_item(  # type: ignore
                    "mounts",
                    crd.MountOverlay(
                        envName=env,
                        name=config.name,
                        mountPath=config.mount_path,
                        source=config.source_config,
                        subPaths=config.sub_paths,
                    ),
                )


class SvcDiscoveryManifestConstructor(ManifestConstructor):
    """Construct the svc discovery part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        try:
            svc_disc_config = SvcDiscConfig.objects.get(application=module.application)
        except SvcDiscConfig.DoesNotExist:
            return

        bk_saas = [crd.SvcDiscEntryBkSaaS(**dict_to_camel(item.dict())) for item in svc_disc_config.bk_saas]
        model_res.spec.svcDiscovery = crd.SvcDiscConfig(bkSaaS=bk_saas)


class DomainResolutionManifestConstructor(ManifestConstructor):
    """Construct the domain resolution part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        try:
            domain_res = DomainResolution.objects.get(application=module.application)
        except DomainResolution.DoesNotExist:
            return

        model_res.spec.domainResolution = crd.DomainResolution(
            nameservers=domain_res.nameservers, hostAliases=domain_res.host_aliases
        )


class ObservabilityManifestConstructor(ManifestConstructor):
    """Construct the observability part."""

    def apply_to(self, model_res: crd.BkAppResource, module: Module):
        try:
            observability = ObservabilityConfig.objects.get(module=module)
        except ObservabilityConfig.DoesNotExist:
            return

        if observability.monitoring:
            model_res.spec.observability = crd.Observability(
                **dict_to_camel({"monitoring": observability.monitoring.dict()})
            )


def get_manifest(module: Module) -> List[Dict]:
    """Get the manifest of current module, the result might contain multiple items."""
    return [
        get_bkapp_resource(module).to_deployable(),
    ]


def get_bkapp_resource(module: Module) -> crd.BkAppResource:
    """Get the manifest of current module.

    :param module: The module object.
    :returns: The resource object.
    """
    builders: List[ManifestConstructor] = [
        BuiltinAnnotsManifestConstructor(),
        AddonsManifestConstructor(),
        AccessControlManifestConstructor(),
        TenantGuardManifestConstructor(),
        ProcessesManifestConstructor(),
        HooksManifestConstructor(),
        BuildConfigManifestConstructor(),
        EnvVarsManifestConstructor(),
        MountsManifestConstructor(),
        SvcDiscoveryManifestConstructor(),
        DomainResolutionManifestConstructor(),
        ObservabilityManifestConstructor(),
    ]
    obj = crd.BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2,
        metadata=ObjectMetadata(name=generate_bkapp_name(module)),
        spec=crd.BkAppSpec(),
    )
    for builder in builders:
        builder.apply_to(obj, module)
    return obj


def get_bkapp_resource_for_deploy(
    env: ModuleEnvironment,
    deploy_id: str,
    deployment: Deployment,
    force_image: Optional[str] = None,
    image_pull_policy: Optional[str] = None,
) -> crd.BkAppResource:
    """Get the BkApp manifest for deploy.

    :param env: The environment object.
    :param deploy_id: The ID of the AppModelDeploy object.
    :param deployment: The related deployment instance.
    :param force_image: If given, set the image of the application to this value.
    :param image_pull_policy: If given, set the imagePullPolicy to this value.
    :returns: The BkApp resource that is ready for deploying.
    """
    model_res = get_bkapp_resource(env.module)

    if force_image:
        if not model_res.spec.build:
            model_res.spec.build = crd.BkAppBuildConfig()
        model_res.spec.build.image = force_image

    if image_pull_policy:
        if not model_res.spec.build:
            model_res.spec.build = crd.BkAppBuildConfig()
        model_res.spec.build.imagePullPolicy = image_pull_policy

    # Set log collector type to inform operator do some special logic.
    # such as: if log collector type is set to "ELK", the operator should mount app logs to host path
    model_res.metadata.annotations[LOG_COLLECTOR_TYPE_ANNO_KEY] = get_log_collector_type(env)

    # 设置上一次部署的状态
    model_res.metadata.annotations[LAST_DEPLOY_STATUS_ANNO_KEY] = _get_last_deploy_status(env, deployment)

    # 由于 bkapp 新增了 process services 配置特性，默认启用
    model_res.set_proc_services_annotation("true")

    # Apply other changes to the resource
    apply_env_annots(model_res, env, deploy_id=deploy_id)
    apply_builtin_env_vars(model_res, env)

    # 将出口集群信息注入到 model_res 中
    apply_egress_annotations(model_res, env)

    # 如果模块是通过 buildpack 构建的，则需要更新 hooks 和 processes 中的 command/args
    mgr = ModuleRuntimeManager(env.module)
    if mgr.build_config.build_method == RuntimeType.BUILDPACK:
        _update_cmd_args_from_wl_build(model_res, WlBuild.objects.get(uuid=deployment.build_id))

    # TODO: Missing parts: "build"
    return model_res


def apply_env_annots(model_res: crd.BkAppResource, env: ModuleEnvironment, deploy_id: Optional[str] = None):
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


def apply_builtin_env_vars(model_res: crd.BkAppResource, env: ModuleEnvironment):
    """Apply the builtin environment vars to the resource object. These vars are hidden from
    the default manifest view and should only be used in the deploying procedure.

    :param model_res: The model resource object, it will be modified in-place.
    :param env: The environment object.
    """
    env_vars = [crd.EnvVar(name="PORT", value=str(settings.CONTAINER_PORT))]

    environment = env.environment
    builtin_env_vars_overlay = [
        crd.EnvVarOverlay(envName=environment, name="PORT", value=str(settings.CONTAINER_PORT))
    ]

    # 此处，云原生应用忽略这些类型的环境变量：用户手动定义、描述文件定义、服务发现，
    # 忽略用户手动定义（include_config_vars）是因为 EnvVarsManifestConstructor 已处理过。
    system_vars = UnifiedEnvVarsReader(env).get_kv_map(
        exclude_sources=[
            # 用户在产品或描述文件手动定义，已经由 EnvVarsManifestConstructor 处理
            EnvVarSource.USER_CONFIGURED,
            EnvVarSource.USER_PRESET,
            # 服务发现环境变量，已经由 SvcDiscoveryManifestConstructor 处理，无需在模型主动添加环境变量
            EnvVarSource.BUILTIN_SVC_DISC,
            # 云原生应用不需要在构建镜像中推送制品到 blobstore，因此忽略
            EnvVarSource.BUILTIN_BLOBSTORE,
        ]
    )
    for name, value in system_vars.items():
        env_vars.append(crd.EnvVar(name=name, value=value))
        builtin_env_vars_overlay.append(crd.EnvVarOverlay(envName=environment, name=name, value=value))

    # Merge the variables, the builtin env vars will override the existed ones
    model_res.spec.configuration.env = merge_env_vars(model_res.spec.configuration.env, env_vars)

    if builtin_env_vars_overlay:
        overlay = model_res.spec.envOverlay
        if not overlay:
            overlay = model_res.spec.envOverlay = crd.EnvOverlay(envVariables=[])
        overlay.envVariables = override_env_vars_overlay(overlay.envVariables or [], builtin_env_vars_overlay)


def apply_egress_annotations(model_res: crd.BkAppResource, env: ModuleEnvironment):
    """Apply egress annotations to the resource object.

    :param model_res: The model resource object, it will be modified in-place.
    :param env: The environment object.
    """
    try:
        binding = RCStateAppBinding.objects.get(app=env.wl_app)
    except RCStateAppBinding.DoesNotExist:
        pass
    else:
        model_res.metadata.annotations[EGRESS_CLUSTER_STATE_NAME_ANNO_KEY] = binding.state.name


def _update_cmd_args_from_wl_build(model_res: crd.BkAppResource, wl_build: WlBuild):
    """从 WlBuild 的构建元数据中获取 entrypoint/command, 并将其更新或替换到 model_res 的 hooks 和 processes 配置中,
    确保最终配置符合基于 buildpack 构建的容器镜像运行规范
    """
    if model_res.spec.hooks and model_res.spec.hooks.preRelease:
        command = wl_build.get_universal_entrypoint() + (model_res.spec.hooks.preRelease.command or [])
        model_res.spec.hooks.preRelease.command = command

    for proc in model_res.spec.processes:
        proc.args = wl_build.get_command_for_proc(proc.name, "")
        proc.command = wl_build.get_entrypoint_for_proc(proc.name)


def _get_last_deploy_status(env: ModuleEnvironment, deployment: Deployment) -> str:
    """获取上一次部署的状态"""
    try:
        latest_dp = Deployment.objects.filter_by_env(env).filter(created__lt=deployment.created).latest("created")
    except Deployment.DoesNotExist:
        return ""
    else:
        return latest_dp.status
