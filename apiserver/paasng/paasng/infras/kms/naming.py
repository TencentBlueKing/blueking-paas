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

"""KMS 凭证相关的命名、OpenBao 路径与 role 推导

- OpenBao 逻辑路径：{tenant_id}/{scope_type}/{scope_name}/{credential_type}/{credential_name}
- 消费 role：{tenant_id}.{scope_type}.{scope_name}.{credential_type}.{credential_name}
"""

import re

from .constants import CREDENTIAL_NAME_MAX_CHARS, CREDENTIAL_TYPE_SECRET, K8S_NAME_MAX_CHARS
from .exceptions import KMSValidationError

_CREDENTIAL_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_K8S_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$")
_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_VERSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def validate_credential_name(name: str) -> None:
    """凭证名会进入 OpenBao 路径和 role，只允许小写字母、数字与短横线"""
    if not name or len(name) > CREDENTIAL_NAME_MAX_CHARS or not _CREDENTIAL_NAME_RE.match(name):
        raise KMSValidationError(
            f"credential name must be 1 to {CREDENTIAL_NAME_MAX_CHARS} lowercase letters, digits or hyphens"
        )


def validate_k8s_name(name: str) -> None:
    """校验 Kubernetes 资源名（DNS 子域名格式）"""
    if not name or len(name) > K8S_NAME_MAX_CHARS or not _K8S_NAME_RE.match(name):
        raise KMSValidationError(f"invalid kubernetes resource name: {name!r}")


def build_openbao_key(*, tenant_id: str, scope_type: str, scope_name: str, credential_name: str) -> str:
    """凭证在 OpenBao 中的逻辑路径（不含 KV v2 的 data 段），用作 ExternalSecret 的 remoteRef.key"""
    return "/".join(_credential_segments(tenant_id, scope_type, scope_name, credential_name))


def build_kms_role(*, tenant_id: str, scope_type: str, scope_name: str, credential_name: str) -> str:
    """KMS 为凭证自动生成的消费 role，用作 Kubernetes 认证的 role 参数"""
    return ".".join(_credential_segments(tenant_id, scope_type, scope_name, credential_name))


def build_credential_name(*, app_code: str, module_name: str, env_name: str, version_id: str) -> str:
    """按配置版本生成凭证名，不按部署 ID 生成

    格式为 {app_code}-{module_name}-{env_name}-{版本 ID 的 32 位十六进制}。前缀过长时截断，
    版本 ID 保证唯一。
    """
    suffix = version_id.replace("-", "").lower()
    if not _VERSION_ID_RE.match(suffix):
        raise KMSValidationError("config version id must be a UUID")
    prefix = _sanitize_label(f"{app_code}-{module_name}-{env_name}")
    prefix = prefix[: CREDENTIAL_NAME_MAX_CHARS - len(suffix) - 1].strip("-") or "kms"
    name = f"{prefix}-{suffix}"
    validate_credential_name(name)
    return name


def build_resource_name(*, tenant_id: str, credential_name: str) -> str:
    """ClusterSecretStore、ExternalSecret 与目标 Secret 共用的名称

    ClusterSecretStore 是集群级资源，名称需在集群内唯一，因此包含租户；凭证名已包含应用、模块、环境与配置版本。
    """
    validate_credential_name(credential_name)
    base = _sanitize_label(tenant_id)
    name = f"kms-{base}-{credential_name}"
    validate_k8s_name(name)
    return name


def build_service_account_name(*, app_code: str, module_name: str, env_name: str) -> str:
    """每个模块环境一个长期复用的专用 SA，名称不含配置版本"""
    base = _sanitize_label(f"{app_code}-{module_name}-{env_name}")
    name = f"{base}-kms"
    validate_k8s_name(name)
    return name


def _sanitize_label(value: str) -> str:
    """转为 DNS 标签风格：小写，非法字符替换为短横线，并去掉首尾短横线"""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _credential_segments(tenant_id: str, scope_type: str, scope_name: str, credential_name: str) -> list[str]:
    for field, value in (("tenant_id", tenant_id), ("scope_type", scope_type), ("scope_name", scope_name)):
        if not _PATH_SEGMENT_RE.match(value or ""):
            raise KMSValidationError(f"{field} is not a valid path segment")
    validate_credential_name(credential_name)
    return [tenant_id, scope_type, scope_name, CREDENTIAL_TYPE_SECRET, credential_name]
