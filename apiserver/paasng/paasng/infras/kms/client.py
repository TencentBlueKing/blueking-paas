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

"""KMS 管理接口直连客户端

直连 KMS 管理地址，不经过 API 网关。创建凭证时在本地完成混合加密，明文不会离开本进程。
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

from .constants import (
    ANNOTATION_MAX_CHARS,
    CREDENTIAL_TYPE_SECRET,
    CRYPTO_CATEGORY_NORMAL,
    DESCRIPTION_MAX_CHARS,
    ERROR_CODE_RESOURCE_NOT_FOUND,
    K8S_SECRET_MAX_BYTES,
    KMS_TENANT_ID_HEADER,
    KMS_USERNAME_HEADER,
    PLAINTEXT_MAX_CHARS,
    SCOPE_TYPE_CUSTOM,
    SERVICE_ACCOUNT_LIST_MAX_ITEMS,
    SERVICE_ACCOUNT_NAME_MAX_CHARS,
    SUPPORTED_SCOPE_TYPES,
)
from .envelope import CryptoInfo, hybrid_encrypt
from .exceptions import KMSAPIError, KMSConfigError, KMSRequestError, KMSValidationError
from .naming import validate_credential_name

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KMSScope:
    """凭证所属的资源范围，对应接口中的 scope 对象"""

    scope_id: int
    scope_type: str = SCOPE_TYPE_CUSTOM

    def __post_init__(self):
        if self.scope_type not in SUPPORTED_SCOPE_TYPES:
            raise KMSValidationError(f"unsupported scope_type: {self.scope_type}")
        if self.scope_id <= 0:
            raise KMSValidationError("scope_id must be a positive integer")

    def to_dict(self) -> dict[str, Any]:
        return {"scope_type": self.scope_type, "scope_id": self.scope_id}


@dataclass(frozen=True)
class ServiceAccountAuth:
    """允许消费凭证的 ServiceAccount 范围

    创建凭证时两个列表都必须是具体取值的非空列表，不能省略（省略即不限制）或使用 "*"。
    """

    name_list: tuple[str, ...]
    namespace_list: tuple[str, ...]


@dataclass(frozen=True)
class CredentialInfo:
    """凭证的元数据。接口响应不包含 value，无法借此取回原文"""

    credential_id: int
    scope: KMSScope
    name: str
    enable_encrypt: bool
    auth: ServiceAccountAuth


class KMSClient:
    """KMS 管理接口客户端。不做自动重试：业务错误抛出 KMSAPIError，其他通信问题抛出 KMSRequestError"""

    def __init__(
        self,
        base_url: str,
        username: str,
        tenant_id: str,
        timeout: float,
    ):
        if not base_url:
            raise KMSConfigError("KMS_API_BASE_URL is not configured")
        if not username:
            raise KMSConfigError("KMS_API_USERNAME is not configured")
        if not tenant_id:
            raise KMSConfigError("tenant_id is required to call KMS")

        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({KMS_USERNAME_HEADER: username, KMS_TENANT_ID_HEADER: tenant_id})

    def get_crypto_info(self) -> CryptoInfo:
        """获取服务端下发的加密算法与公钥。公钥可能变化，调用方不应长期缓存结果"""
        data = self._request("POST", "/api/v1/get/crypto_info", {"category": CRYPTO_CATEGORY_NORMAL})
        with _parsing_response("crypto_info"):
            crypto = data["crypto"]
            return CryptoInfo(
                asymmetric_type=str(crypto["asymmetric_type"]),
                symmetric_type=str(crypto["symmetric_type"]),
                symmetric_mode=str(crypto["symmetric_mode"]),
                public_key=str(data["public_key"]),
            )

    def encrypt_credential_value(self, plaintext: str) -> str:
        """在本地把明文加密为 KMS 信封。同一明文两次加密的结果不同，不能用密文比对内容

        :raises KMSValidationError: 明文超出上限，或信封超出 Secret 容量限制
        :raises KMSCryptoError: 服务端加密信息不受支持
        :raises KMSRequestError: 获取加密信息时网络或响应异常
        """
        _validate_length("plaintext", plaintext, PLAINTEXT_MAX_CHARS)
        envelope = hybrid_encrypt(plaintext, self.get_crypto_info())
        _validate_envelope(envelope)
        return envelope

    def create_credential_from_envelope(
        self,
        *,
        scope: KMSScope,
        name: str,
        envelope: str,
        auth: ServiceAccountAuth,
        description: str = "",
        annotation: str = "",
    ) -> int:
        """用 encrypt_credential_value 生成的信封创建 secret 凭证（固定开启落地存储加密），返回 credential_id

        :raises KMSValidationError: 参数超出接口约束，此时尚未发起远程请求
        :raises KMSAPIError: KMS 返回业务错误
        :raises KMSRequestError: 网络、超时或响应异常。结果可能已生效，调用方应按名称核对
        """
        validate_credential_name(name)
        _validate_length("description", description, DESCRIPTION_MAX_CHARS)
        _validate_length("annotation", annotation, ANNOTATION_MAX_CHARS)
        _validate_service_account_auth(auth)
        _validate_envelope(envelope)

        data = self._request(
            "POST",
            "/api/v1/credential",
            {
                "scope": scope.to_dict(),
                "metadata": {
                    "type": CREDENTIAL_TYPE_SECRET,
                    "name": name,
                    "alias_name": name,
                    "value": envelope,
                    "enable_encrypt": True,
                    "description": description,
                    "annotation": annotation,
                },
                "auth": {
                    "service_account": {
                        "name_list": list(auth.name_list),
                        "namespace_list": list(auth.namespace_list),
                    }
                },
            },
        )
        with _parsing_response("credential"):
            credential_id = int(data["credential_id"])
        logger.info("KMS credential created, credential_id: %s, name: %s", credential_id, name)
        return credential_id

    def find_credential(self, *, scope: KMSScope, name: str) -> CredentialInfo | None:
        """按名称查询 secret 凭证，不存在时返回 None"""
        validate_credential_name(name)
        try:
            data = self._request(
                "POST",
                "/api/v1/get/credential",
                {"scope": scope.to_dict(), "type": CREDENTIAL_TYPE_SECRET, "name": name},
            )
        except KMSAPIError as e:
            if e.code == ERROR_CODE_RESOURCE_NOT_FOUND:
                return None
            raise
        return _parse_credential(data)

    def delete_credential(self, credential_id: int) -> None:
        """删除凭证。调用方需先确认已无消费者（例如对应 Secret 已回收）"""
        self._request("DELETE", "/api/v1/credential", {"credential_id": credential_id})
        logger.info("KMS credential deleted, credential_id: %s", credential_id)

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """发起请求，返回响应中的 data。业务 code 非 0 时抛出 KMSAPIError"""
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.request(method, url, json=body, timeout=self._timeout)
        except requests.RequestException as e:
            raise KMSRequestError(f"KMS {method} {path} transport error: {e}") from e

        payload = _decode_json_object(resp)
        code = payload.get("code") if payload is not None else None
        # 业务错误以响应中的 code 为准，不论 HTTP 状态码为何
        if payload is not None and isinstance(code, int) and code != 0:
            raise KMSAPIError(code, str(payload.get("message") or ""))
        if not 200 <= resp.status_code < 300:
            raise KMSRequestError(f"KMS {method} {path} returned HTTP {resp.status_code}", resp.status_code)
        if payload is None or code != 0:
            raise KMSRequestError(f"KMS {method} {path} returned an unexpected response")

        data = payload.get("data") or {}
        if not isinstance(data, dict):
            raise KMSRequestError(f"KMS {method} {path} returned unexpected data")
        return data


def make_kms_client(tenant_id: str) -> KMSClient:
    """按 Django settings 构造 KMS 客户端

    :param tenant_id: 请求头 X-Bk-Tenant-Id 的取值，由调用方依据已授权的模块环境传入
    :raises KMSConfigError: KMS_API_BASE_URL 或 KMS_API_USERNAME 未配置
    """
    return KMSClient(
        base_url=settings.KMS_API_BASE_URL,
        username=settings.KMS_API_USERNAME,
        tenant_id=tenant_id,
        timeout=float(settings.KMS_API_TIMEOUT_SECONDS),
    )


def _validate_length(field: str, value: str, max_chars: int) -> None:
    if len(value) > max_chars:
        raise KMSValidationError(f"{field} must not exceed {max_chars} characters")


def _validate_envelope(envelope: str) -> None:
    """信封为 ASCII 字符串，字符数即字节数，超出 Secret 容量时无法同步到容器"""
    if not envelope or len(envelope) > K8S_SECRET_MAX_BYTES:
        raise KMSValidationError("encrypted credential is empty or exceeds the Kubernetes Secret size limit")


def _validate_service_account_auth(auth: ServiceAccountAuth) -> None:
    """授权范围必须是具体、非空的列表，不能省略或使用通配符"""
    for field, values in (("name_list", auth.name_list), ("namespace_list", auth.namespace_list)):
        if not values or len(values) > SERVICE_ACCOUNT_LIST_MAX_ITEMS:
            raise KMSValidationError(
                f"service_account.{field} must contain 1 to {SERVICE_ACCOUNT_LIST_MAX_ITEMS} items"
            )
        for item in values:
            if not item or item == "*" or len(item) > SERVICE_ACCOUNT_NAME_MAX_CHARS:
                raise KMSValidationError(f"service_account.{field} contains an invalid item")


def _parse_credential(data: dict[str, Any]) -> CredentialInfo:
    with _parsing_response("credential"):
        metadata, scope = data["metadata"], data["scope"]
        service_account = (data.get("auth") or {}).get("service_account") or {}
        # 响应未返回授权列表即表示不限制，用 "*" 标记，使其与期望的具体授权比对时不一致
        name_list = service_account.get("name_list") or ["*"]
        namespace_list = service_account.get("namespace_list") or ["*"]
        return CredentialInfo(
            credential_id=int(metadata["credential_id"]),
            scope=KMSScope(scope_id=int(scope["scope_id"]), scope_type=str(scope["scope_type"])),
            name=str(metadata["name"]),
            enable_encrypt=metadata.get("enable_encrypt") is True,
            auth=ServiceAccountAuth(name_list=tuple(name_list), namespace_list=tuple(namespace_list)),
        )


def _decode_json_object(resp: requests.Response) -> dict[str, Any] | None:
    try:
        payload = resp.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


@contextmanager
def _parsing_response(name: str) -> Iterator[None]:
    """响应缺少字段或类型不符时，统一转换为 KMSRequestError"""
    try:
        yield
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise KMSRequestError(f"KMS returned an invalid {name} response") from e
