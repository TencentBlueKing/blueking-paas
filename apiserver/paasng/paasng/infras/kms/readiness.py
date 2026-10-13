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

"""ExternalSecret 与目标 Secret 的就绪判定

返回的 reason 会写入数据库，只能包含固定分类或 ESO 条件的 reason 字段，不能包含 Secret 内容或 ESO 条件的 message。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .constants import SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY
from .manifests import EXTERNAL_SECRET_KIND

ESO_READY_CONDITION_TYPE = "Ready"
ESO_CONDITION_STATUS_TRUE = "True"


@dataclass(frozen=True)
class SecretReadiness:
    """就绪判定结果。reason 为未就绪原因，就绪时固定为 ready"""

    ready: bool
    reason: str


def evaluate_secret_readiness(
    *,
    external_secret: Mapping[str, Any] | None,
    secret: Mapping[str, Any] | None,
    expected_external_secret_uid: str,
) -> SecretReadiness:
    """判断 ExternalSecret 是否已把凭证同步到目标 Secret

    :param external_secret: 从集群读取的 ExternalSecret 对象，不存在时为 None
    :param secret: 从集群读取的目标 Secret 对象（由 ESO 创建），不存在时为 None
    :param expected_external_secret_uid: 提交 ExternalSecret 时记录的 UID，用于排除同名的旧对象

    就绪需同时满足：
    - ExternalSecret 的 UID 与提交时记录的一致，Ready 条件为 True，且已有 refreshTime；
    - 目标 Secret 存在，且 ownerReference 指向该 ExternalSecret（creationPolicy 为 Owner 时由 ESO 设置）；
    - 目标 Secret 同时包含 envelope 与 privateKey 两个非空字段。
    """
    if external_secret is None:
        return _not_ready("external_secret_missing")

    es_metadata = _as_mapping(external_secret.get("metadata"))
    es_name = str(es_metadata.get("name") or "")
    es_uid = str(es_metadata.get("uid") or "")
    if not expected_external_secret_uid or es_uid != expected_external_secret_uid:
        return _not_ready("external_secret_uid_mismatch")
    if reason := _external_secret_unready_reason(external_secret):
        return _not_ready(reason)
    if reason := _secret_unready_reason(secret, es_name=es_name, es_uid=es_uid):
        return _not_ready(reason)
    return SecretReadiness(ready=True, reason="ready")


def _not_ready(reason: str) -> SecretReadiness:
    return SecretReadiness(ready=False, reason=reason)


def _external_secret_unready_reason(external_secret: Mapping[str, Any]) -> str | None:
    """ExternalSecret 尚未完成同步时返回原因，否则返回 None"""
    status = _as_mapping(external_secret.get("status"))
    ready_condition = _find_ready_condition(status)
    if ready_condition is None or ready_condition.get("status") != ESO_CONDITION_STATUS_TRUE:
        reason = str((ready_condition or {}).get("reason") or "unknown")
        return f"external_secret_not_ready:{reason}"
    if not status.get("refreshTime"):
        return "external_secret_not_refreshed"
    return None


def _secret_unready_reason(secret: Mapping[str, Any] | None, *, es_name: str, es_uid: str) -> str | None:
    """目标 Secret 不满足就绪条件时返回原因，否则返回 None"""
    if secret is None:
        return "secret_missing"
    metadata = _as_mapping(secret.get("metadata"))
    if not _is_owned_by(metadata, kind=EXTERNAL_SECRET_KIND, name=es_name, uid=es_uid):
        return "secret_owner_mismatch"
    data = _as_mapping(secret.get("data"))
    if not all(data.get(key) for key in (SECRET_KEY_ENVELOPE, SECRET_KEY_PRIVATE_KEY)):
        return "secret_data_missing"
    return None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _find_ready_condition(status: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for condition in status.get("conditions") or []:
        if isinstance(condition, Mapping) and condition.get("type") == ESO_READY_CONDITION_TYPE:
            return condition
    return None


def _is_owned_by(metadata: Mapping[str, Any], *, kind: str, name: str, uid: str) -> bool:
    if not name or not uid:
        return False
    return any(
        isinstance(ref, Mapping) and ref.get("kind") == kind and ref.get("name") == name and ref.get("uid") == uid
        for ref in metadata.get("ownerReferences") or []
    )
