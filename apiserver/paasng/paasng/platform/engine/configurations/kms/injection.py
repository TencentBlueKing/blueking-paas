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
from paas_wl.bk_app.processes.entities import SecretFileMount
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.configurations.config_var import get_env_variables
from paasng.platform.engine.configurations.env_var.encryption import (
    ENCRYPTED_KEYS_ENV_NAME,
    SECRET_KEY_ENV_VAR_NAME,
    collect_sensitive_keys,
    is_encrypted_value,
)
from paasng.platform.engine.exceptions import DeployShouldAbortError
from paasng.platform.modules.models import Module

# 敏感变量加密时写入的元数据变量。托管给 KMS 后，没有剩余密文时不再需要
_ENCRYPTION_METADATA_NAMES = frozenset({SECRET_KEY_ENV_VAR_NAME, ENCRYPTED_KEYS_ENV_NAME})

# 即使被标记为敏感，也继续作为环境变量注入的内置变量
KMS_UNMANAGED_ENV_KEYS = frozenset({"BKPAAS_APP_SECRET"})


def is_kms_injection_enabled(env: ModuleEnvironment) -> bool:
    return env.application.feature_flag.has_feature(AppFeatureFlag.KMS_SECRET_INJECTION)


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


def split_kms_managed_env_vars(env: ModuleEnvironment) -> tuple[dict[str, str], dict[str, str]]:
    """把环境变量拆分为（普通变量，由 KMS 托管的敏感变量）"""
    managed_keys = collect_kms_managed_keys(env)
    all_values = get_env_variables(env)
    plain = {key: value for key, value in all_values.items() if key not in managed_keys}
    managed = {key: value for key, value in all_values.items() if key in managed_keys}
    return plain, managed


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
    if not _has_encrypted_values(bkapp_res):
        overlay.envVariables = [var for var in overlay.envVariables if var.name not in _ENCRYPTION_METADATA_NAMES]


def add_kms_secret_mount(bkapp_res: crd.BkAppResource, env_name: str, mount: SecretFileMount) -> None:
    """在环境覆盖项中追加 KMS Secret 挂载。operator 会把它应用到业务进程与云原生 Hook 的容器上"""
    _ensure_mount_not_reserved(bkapp_res, env_name, mount)
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


def _has_encrypted_values(bkapp_res: crd.BkAppResource) -> bool:
    values = [var.value for var in bkapp_res.spec.configuration.env]
    overlay = bkapp_res.spec.envOverlay
    if overlay is not None and overlay.envVariables:
        values.extend(var.value for var in overlay.envVariables)
    return any(is_encrypted_value(value) for value in values)


def _ensure_mount_not_reserved(bkapp_res: crd.BkAppResource, env_name: str, mount: SecretFileMount) -> None:
    """用户自定义挂载不得占用 KMS 的卷名或目录，否则 Pod 规格会冲突，或者覆盖保留路径"""
    mounts: list[crd.Mount | crd.MountOverlay] = list(bkapp_res.spec.mounts or [])
    if bkapp_res.spec.envOverlay is not None:
        mounts.extend(m for m in bkapp_res.spec.envOverlay.mounts or [] if m.envName == env_name)

    reserved_dir = mount.mount_dir.rstrip("/")
    for user_mount in mounts:
        if (
            user_mount.name == mount.volume_name
            or user_mount.mountPath == reserved_dir
            or user_mount.mountPath.startswith(reserved_dir + "/")
        ):
            raise DeployShouldAbortError(f"挂载路径 {user_mount.mountPath} 与 KMS 保留的挂载冲突，请修改后重新部署")
