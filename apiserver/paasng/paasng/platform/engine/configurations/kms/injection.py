# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
"""发布时的 KMS 接入：决定哪些敏感变量交给 KMS 托管，并调整 BkApp 中的环境变量与挂载"""

from collections.abc import Mapping

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.workloads.release_controller.entities import SecretFileMount
from paasng.infras.kms.constants import KMS_ENABLED_ENV_VAR_NAME, KMS_SECRET_MOUNT_DIR, KMS_SECRET_VOLUME_NAME
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.config_var import get_env_variables
from paasng.platform.engine.configurations.env_var.encryption import KMS_UNMANAGED_ENV_KEYS, collect_sensitive_keys
from paasng.platform.engine.exceptions import DeployShouldAbortError
from paasng.platform.engine.models import Deployment
from paasng.platform.modules.models import Module

from .provisioner import provision_kms_secret


def ensure_kms_injection_supported(env: ModuleEnvironment) -> None:
    """拒绝尚未接入 Secret 挂载的应用类型，避免敏感变量丢失"""
    if env.application.use_isolated_sandbox:
        raise DeployShouldAbortError("开启 KMS 托管敏感变量后，暂不支持隔离沙箱应用")


def collect_kms_managed_keys(env: ModuleEnvironment) -> frozenset[str]:
    """环境中由 KMS 托管的敏感变量键：用户标记为敏感的变量，以及增强服务的隐藏/移除字段"""
    return frozenset(collect_sensitive_keys(env)) - KMS_UNMANAGED_ENV_KEYS


def collect_kms_managed_keys_by_env(module: Module) -> dict[str, frozenset[str]]:
    """模块各环境的 KMS 托管键，用于从云原生 BkApp 中剥离敏感变量"""
    return {env.environment: collect_kms_managed_keys(env) for env in module.envs.all()}


def split_kms_managed_env_vars(
    env: ModuleEnvironment, managed_keys: frozenset[str] | None = None
) -> tuple[dict[str, str], dict[str, str]]:
    """把环境变量拆分为（普通变量，由 KMS 托管的敏感变量）

    :param managed_keys: 已经算好的托管键。不传时重新收集，传入可以保证与剥离 BkApp 时使用同一份结果
    """
    if managed_keys is None:
        managed_keys = collect_kms_managed_keys(env)

    all_values = get_env_variables(env)
    plain = {key: value for key, value in all_values.items() if key not in managed_keys}
    managed = {key: value for key, value in all_values.items() if key in managed_keys}
    return plain, managed


def prepare_kms_process_env(
    env: ModuleEnvironment, deployment: Deployment
) -> tuple[dict[str, str], list[SecretFileMount]]:
    """普通应用的进程与 pre_release 命令：返回（普通环境变量，需要挂载的 KMS Secret 文件）

    同一次部署中多次调用时，敏感变量内容不变就会复用同一个配置版本，挂载的 Secret 相同。
    """
    ensure_kms_injection_supported(env)
    plain_values, sensitive_values = split_kms_managed_env_vars(env)
    if not sensitive_values:
        return plain_values, []

    NamespacesHandler.new_by_app(env.wl_app).ensure_namespace(env.wl_app.namespace)
    mount = provision_kms_secret(env, deployment, sensitive_values)
    plain_values[KMS_ENABLED_ENV_VAR_NAME] = "true"
    return plain_values, [mount]


def strip_kms_managed_env_vars(
    bkapp_res: crd.BkAppResource,
    env_name: str,
    managed_keys_by_env: Mapping[str, frozenset[str]],
) -> None:
    """从 BkApp 中移除由 KMS 托管的敏感变量：包括默认配置，以及各环境的覆盖项

    覆盖项按其所属环境的托管键过滤，因此其他环境的敏感值也不会进入本次提交的资源。
    """
    deploy_keys = managed_keys_by_env.get(env_name, frozenset())
    bkapp_res.spec.configuration.env = [var for var in bkapp_res.spec.configuration.env if var.name not in deploy_keys]

    overlay = bkapp_res.spec.envOverlay
    if overlay is None or not overlay.envVariables:
        return

    overlay.envVariables = [
        var for var in overlay.envVariables if var.name not in managed_keys_by_env.get(var.envName, frozenset())
    ]


def ensure_kms_mount_available(bkapp_res: crd.BkAppResource, env_name: str) -> None:
    """用户自定义挂载不得占用 KMS 的卷名，也不得挂载到 KMS 目录本身、其子目录或上级目录

    需要在创建 KMS 远端资源之前调用，避免检查失败时凭证与集群资源已经创建。
    """
    mounts: list[crd.Mount | crd.MountOverlay] = list(bkapp_res.spec.mounts or [])
    if bkapp_res.spec.envOverlay is not None:
        mounts.extend(m for m in bkapp_res.spec.envOverlay.mounts or [] if m.envName == env_name)

    reserved_dir = KMS_SECRET_MOUNT_DIR.rstrip("/")
    for user_mount in mounts:
        if user_mount.name == KMS_SECRET_VOLUME_NAME:
            raise DeployShouldAbortError(f"挂载卷名 {user_mount.name} 为 KMS 保留名称，请修改后重新部署")

        user_dir = user_mount.mountPath.rstrip("/")
        if (
            user_dir == reserved_dir
            or _is_parent_dir(user_dir, reserved_dir)
            or _is_parent_dir(reserved_dir, user_dir)
        ):
            raise DeployShouldAbortError(
                f"挂载路径 {user_mount.mountPath} 会与 KMS 保留目录 {KMS_SECRET_MOUNT_DIR} 冲突，请修改后重新部署"
            )


def add_kms_secret_mount(bkapp_res: crd.BkAppResource, env_name: str, mount: SecretFileMount) -> None:
    """追加 KMS Secret 挂载及启用标志。operator 会把它们应用到业务进程及 Hook"""
    if bkapp_res.spec.envOverlay is None:
        bkapp_res.spec.envOverlay = crd.EnvOverlay()

    bkapp_res.spec.envOverlay.append_item(
        "mounts",
        crd.MountOverlay(
            envName=env_name,
            name=mount.volume_name,
            mountPath=mount.mount_dir,
            source=crd.VolumeSource(secret=crd.SecretSource(name=mount.secret_name)),
            subPaths=list(mount.sub_paths),
        ),
    )

    overlay = bkapp_res.spec.envOverlay
    overlay.envVariables = [
        var for var in overlay.envVariables or [] if (var.envName, var.name) != (env_name, KMS_ENABLED_ENV_VAR_NAME)
    ]
    overlay.append_item(
        "envVariables", crd.EnvVarOverlay(envName=env_name, name=KMS_ENABLED_ENV_VAR_NAME, value="true")
    )


def _is_parent_dir(parent: str, child: str) -> bool:
    """parent 为空字符串时表示根目录 /"""
    return child.startswith(parent + "/")
