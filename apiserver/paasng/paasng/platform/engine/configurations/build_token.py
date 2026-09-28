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

"""构建 token：apiserver 为单次构建签发的短期 JWT，构建容器凭它经镜像代理访问平台仓库，替代平台全局仓库账号。

声明、签名算法与 JWKS 格式以《构建镜像代理接口契约 v1》第 3 节为准，修改前需同步更新契约。
"""

import base64
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.entities import BuildMetadata
    from paas_wl.bk_app.applications.models.build import BuildProcess
    from paas_wl.infras.cluster.entities import AppImageRegistry

ISSUER = "bkpaas-apiserver"
AUDIENCE_PREFIX = "bkpaas-registry-proxy:"
CLAIMS_VERSION = 1
SIGNING_ALGORITHM = "EdDSA"
# exp = iat + BUILD_PROCESS_TIMEOUT + TOKEN_GRACE_SECONDS
TOKEN_GRACE_SECONDS = 300

KANIKO_CACHE_REPO_SUFFIX = "/dockerbuild-cache"
CNB_CACHE_TAG = "cnb-build-cache"
ANY_TAG = "*"

_UPSTREAM_ALIAS_REGEX = re.compile(r"[a-z0-9]+(-+[a-z0-9]+)*")
# Docker 镜像 tag 语法，见 https://github.com/distribution/reference
_IMAGE_TAG_REGEX = re.compile(r"[\w][\w.-]{0,127}", re.ASCII)


class BuildTokenUnavailable(Exception):
    """无法为构建签发 token。构建必须直接失败，不得回退为注入平台仓库的真实凭证。"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"image credential unavailable: {reason}")


def make_upstream_alias(host: str) -> str:
    """由上游主机名（含端口）推导上游别名，例如 `registry.local:5000` -> `registry-local-5000`

    :raises ValueError: 推导结果不合法，例如主机为空、为 IPv6 字面量或带协议
    """
    alias = host.lower().replace(".", "-").replace(":", "-")
    if not _UPSTREAM_ALIAS_REGEX.fullmatch(alias):
        raise ValueError(f"can not derive a valid upstream alias from host {host!r}")
    return alias


# ------------------
# 签名密钥
# ------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@dataclass(frozen=True)
class SigningKey:
    """构建 token 的 Ed25519 签名密钥"""

    private_key: Ed25519PrivateKey

    @classmethod
    def generate(cls) -> "SigningKey":
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_pem(cls, pem: str | bytes) -> "SigningKey":
        """从无口令的 PEM 加载私钥

        :raises ValueError: 不是合法的无口令 PEM 私钥
        :raises TypeError: 不是 Ed25519 私钥
        """
        if isinstance(pem, str):
            pem = pem.encode()
        try:
            key = serialization.load_pem_private_key(pem.strip(), password=None)
        except (ValueError, TypeError):
            # 丢弃原始异常，避免密钥内容随异常链进入日志
            raise ValueError("not a valid PEM private key without password") from None
        if not isinstance(key, Ed25519PrivateKey):
            raise TypeError("not an Ed25519 private key")
        return cls(key)

    def to_pem(self) -> bytes:
        return self.private_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )

    @property
    def x(self) -> str:
        raw = self.private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return _b64url(raw)

    @property
    def kid(self) -> str:
        """公钥的 RFC 7638 指纹：必需成员按字典序、无空白序列化后取 SHA-256"""
        members = json.dumps({"crv": "Ed25519", "kty": "OKP", "x": self.x}, separators=(",", ":"))
        return _b64url(hashlib.sha256(members.encode()).digest())

    def public_jwk(self) -> dict[str, str]:
        return {"kty": "OKP", "crv": "Ed25519", "x": self.x, "kid": self.kid, "alg": SIGNING_ALGORITHM, "use": "sig"}

    def __repr__(self) -> str:
        return f"SigningKey(kid={self.kid!r})"


@dataclass(frozen=True)
class SigningKeySet:
    """全部可用的签名密钥，其中 active 用于签发，其余仅保留在 JWKS 中供代理校验轮换前签发的 token"""

    keys: list[SigningKey]
    active: SigningKey

    def to_jwks(self) -> dict[str, list[dict[str, str]]]:
        """导出公钥集合，分发给各集群的镜像代理"""
        return {"keys": [k.public_jwk() for k in self.keys]}


def load_signing_key_set() -> SigningKeySet | None:
    """从配置项 BUILD_TOKEN_SIGNING_KEYS、BUILD_TOKEN_ACTIVE_KID 加载签名密钥，未配置密钥时返回 None

    :raises ImproperlyConfigured: 配置非法。错误信息只包含下标与 kid，不包含密钥内容
    """
    keys = _parse_signing_keys(settings.BUILD_TOKEN_SIGNING_KEYS or [])
    active_kid = settings.BUILD_TOKEN_ACTIVE_KID
    if not keys:
        if active_kid:
            raise ImproperlyConfigured("BUILD_TOKEN_ACTIVE_KID is set but BUILD_TOKEN_SIGNING_KEYS is empty")
        return None

    if not active_kid:
        if len(keys) > 1:
            raise ImproperlyConfigured("BUILD_TOKEN_ACTIVE_KID is required when multiple signing keys are configured")
        return SigningKeySet(keys=keys, active=keys[0])

    for key in keys:
        if key.kid == active_kid:
            return SigningKeySet(keys=keys, active=key)
    raise ImproperlyConfigured(f"BUILD_TOKEN_ACTIVE_KID {active_kid} not found in BUILD_TOKEN_SIGNING_KEYS")


def _parse_signing_keys(raw_keys: Any) -> list[SigningKey]:
    # 通过环境变量配置单把密钥时，取到的是字符串
    if isinstance(raw_keys, (str, bytes)):
        raw_keys = [raw_keys]
    if not isinstance(raw_keys, (list, tuple)):
        raise ImproperlyConfigured("BUILD_TOKEN_SIGNING_KEYS must be a list of PEM encoded Ed25519 private keys")

    keys: list[SigningKey] = []
    for i, pem in enumerate(raw_keys):
        if not isinstance(pem, (str, bytes)):
            raise ImproperlyConfigured(f"BUILD_TOKEN_SIGNING_KEYS[{i}] must be a string")
        try:
            key = SigningKey.from_pem(pem)
        except (ValueError, TypeError) as e:
            raise ImproperlyConfigured(f"BUILD_TOKEN_SIGNING_KEYS[{i}] is invalid: {e}") from None
        if any(k.kid == key.kid for k in keys):
            raise ImproperlyConfigured(f"BUILD_TOKEN_SIGNING_KEYS[{i}] is duplicated, kid: {key.kid}")
        keys.append(key)
    return keys


# ------------------
# 签发
# ------------------


def make_build_token_claims(
    *,
    build_process_id: str,
    app_code: str,
    module_name: str,
    metadata: "BuildMetadata",
    registry: "AppImageRegistry",
    cluster_name: str,
    now: int,
) -> dict[str, Any]:
    """按本次构建推导 token 声明，授权范围仅覆盖本应用本模块的产物与缓存

    :param build_process_id: BuildProcess 的 UUID
    :param registry: 应用的平台仓库，即 `get_image_registry_by_app()` 的返回值
    :param cluster_name: 应用所在集群名，镜像代理以此区分 audience
    :param now: 签发时刻，unix 秒
    :raises BuildTokenUnavailable: 平台仓库配置、构建类型或产物镜像不满足签发条件
    """
    if not registry.host or not registry.namespace:
        raise BuildTokenUnavailable("platform image registry host or namespace is empty")
    if any(not seg for seg in registry.namespace.split("/")):
        raise BuildTokenUnavailable(f"invalid platform image registry namespace: {registry.namespace}")
    try:
        alias = make_upstream_alias(registry.host)
    except ValueError:
        raise BuildTokenUnavailable(
            f"cannot derive an upstream alias from the platform image registry host: {registry.host}"
        ) from None
    if not cluster_name:
        raise BuildTokenUnavailable("cluster name is empty")

    # 与 generate_image_repository_by_env 一致
    repo_path = f"{registry.namespace}/{app_code}/{module_name}"
    image_prefix = f"{registry.host}/{repo_path}:"
    tag = metadata.image.removeprefix(image_prefix)
    if not metadata.image.startswith(image_prefix) or not _IMAGE_TAG_REGEX.fullmatch(tag):
        raise BuildTokenUnavailable(
            f"build image does not belong to this module's platform registry repository: {metadata.image}"
        )

    client_repo = f"{alias}/{repo_path}"
    if metadata.use_dockerfile:
        push = [
            # 允许推送本应用产物（具体 tag）
            {"repo": client_repo, "tags": [tag]},
            # 允许推送 kaniko build-cache
            {"repo": client_repo + KANIKO_CACHE_REPO_SUFFIX, "tags": [ANY_TAG]},
        ]
    elif metadata.use_cnb:
        # CNB 的缓存是产物仓库中的一个 tag，不是独立仓库
        push = [{"repo": client_repo, "tags": list(dict.fromkeys([tag, CNB_CACHE_TAG]))}]
    else:
        raise BuildTokenUnavailable("build token is only supported for Dockerfile and buildpack image builds")

    return {
        "iss": ISSUER,
        "aud": AUDIENCE_PREFIX + cluster_name,
        "sub": build_process_id,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + settings.BUILD_PROCESS_TIMEOUT + TOKEN_GRACE_SECONDS,
        "ver": CLAIMS_VERSION,
        "app_code": app_code,
        "module": module_name,
        "push": push,
        # 平台仓库中其他应用的镜像不可读；本应用的产物与缓存仓库因 push 授权优先于 pull_deny 而可读
        "pull": [f"{alias}/"],
        "pull_deny": [f"{alias}/{registry.namespace}/"],
    }


def sign_build_token(claims: dict[str, Any], key: SigningKey) -> str:
    return jwt.encode(
        claims, key.to_pem().decode(), algorithm=SIGNING_ALGORITHM, headers={"kid": key.kid, "typ": "JWT"}
    )


def issue_build_token(
    bp: "BuildProcess",
    metadata: "BuildMetadata",
    registry: "AppImageRegistry",
    cluster_name: str,
    now: int | None = None,
) -> str:
    """为构建签发构建 token。返回值等同于凭证，不得写入日志

    :param registry: 应用的平台仓库，即 `get_image_registry_by_app(bp.app)` 的返回值
    :param cluster_name: 应用所在集群名，即 `get_cluster_by_app(bp.app).name`
    :param now: 签发时刻，unix 秒，默认为当前时刻
    :raises BuildTokenUnavailable: 未配置签名密钥，或本次构建不满足签发条件
    """
    try:
        keyset = load_signing_key_set()
    except ImproperlyConfigured:
        raise BuildTokenUnavailable("invalid build token signing key configuration") from None
    if not keyset:
        raise BuildTokenUnavailable("build token signing key is not configured")

    wl_app = bp.app
    claims = make_build_token_claims(
        # 统一为带连字符的 36 位格式
        build_process_id=str(uuid.UUID(str(bp.uuid))),
        app_code=wl_app.paas_app_code,
        module_name=wl_app.module_name,
        metadata=metadata,
        registry=registry,
        cluster_name=cluster_name,
        now=int(time.time()) if now is None else now,
    )
    return sign_build_token(claims, keyset.active)
