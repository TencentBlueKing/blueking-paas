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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from paasng.platform.engine.configurations.image import (
    CNB_CACHE_TAG,
    kaniko_cache_repository,
    module_image_repository,
    module_repo_path,
)

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
# 授权范围
# ------------------


@dataclass(frozen=True)
class BuildTokenScope:
    """构建 token 的授权范围，仓库路径均为代理视角：<上游别名>/<上游仓库路径>

    :param push: 可推送的仓库（精确匹配）与 tag
    :param pull: 可拉取的仓库，以 / 结尾为前缀匹配
    :param pull_deny: 禁止拉取的仓库，优先于 pull；push 授权的仓库不受其限制
    """

    push: list[dict[str, Any]]
    pull: list[str]
    pull_deny: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BuildTokenAudit:
    """构建 token 中仅用于审计的声明，与镜像代理审计日志的字段一一对应，代理不据此授权

    :param app_code: 应用构建为应用 code；沙箱镜像构建为调用构建 API 的蓝鲸应用 code
    :param module: 模块名，沙箱镜像构建为空串
    """

    app_code: str
    module: str = ""

    def to_claims(self) -> dict[str, dict[str, str]]:
        return {"app": {"code": self.app_code, "module": self.module}}


def get_registry_upstream_alias(host: str, namespace: str) -> str:
    """校验平台仓库的 host 与 namespace，返回其在代理中的上游别名

    :raises BuildTokenUnavailable: host、namespace 为空或非法
    """
    if not host or not namespace:
        raise BuildTokenUnavailable("platform image registry host or namespace is empty")
    if any(not seg for seg in namespace.split("/")):
        raise BuildTokenUnavailable(f"invalid platform image registry namespace: {namespace}")
    try:
        return make_upstream_alias(host)
    except ValueError:
        raise BuildTokenUnavailable(
            f"cannot derive an upstream alias from the platform image registry host: {host}"
        ) from None


def extract_image_tag(image: str, repository: str, owner: str) -> str:
    """校验产物镜像位于平台按规则推导出的仓库中，返回其 tag。不信任调用方传入的产物地址，避免授权越出本次构建

    :param owner: 仓库归属的描述，仅用于错误信息
    :raises BuildTokenUnavailable: 产物镜像不在该仓库中，或不是合法的 tag 引用
    """
    image_prefix = f"{repository}:"
    tag = image.removeprefix(image_prefix)
    if not image.startswith(image_prefix) or not _IMAGE_TAG_REGEX.fullmatch(tag):
        raise BuildTokenUnavailable(f"build image does not belong to {owner}: {image}")
    return tag


def make_module_build_scope(
    app_code: str, module_name: str, metadata: "BuildMetadata", registry: "AppImageRegistry"
) -> BuildTokenScope:
    """应用模块构建的授权范围：仅覆盖本应用本模块的产物与缓存

    :param registry: 应用的平台仓库，即 `get_image_registry_by_app()` 的返回值
    :raises BuildTokenUnavailable: 平台仓库配置、构建类型或产物镜像不满足签发条件
    """
    alias = get_registry_upstream_alias(registry.host, registry.namespace)

    # 与 generate_image_repository_by_env 共用 module_image_repository；代理侧仓库用上游别名替换 host
    repo_path = module_repo_path(registry.namespace, app_code, module_name)
    repository = module_image_repository(registry.host, registry.namespace, app_code, module_name)
    tag = extract_image_tag(metadata.image, repository, "this module's platform registry repository")

    client_repo = f"{alias}/{repo_path}"
    if metadata.use_dockerfile:
        push = [
            # 允许推送本应用产物（具体 tag）
            {"repo": client_repo, "tags": [tag]},
            # 允许推送 kaniko build-cache
            {"repo": kaniko_cache_repository(client_repo), "tags": [ANY_TAG]},
        ]
    elif metadata.use_cnb:
        # CNB 的缓存是产物仓库中的一个 tag，不是独立仓库
        push = [{"repo": client_repo, "tags": list(dict.fromkeys([tag, CNB_CACHE_TAG]))}]
    else:
        raise BuildTokenUnavailable("build token is only supported for Dockerfile and buildpack image builds")

    # 平台仓库中的镜像（含其他应用的产物）均可读，推送仅限本应用本模块
    return BuildTokenScope(push=push, pull=[f"{alias}/"])


# ------------------
# 签发
# ------------------


def make_build_token_claims(
    *,
    subject: str,
    cluster_name: str,
    ttl: int,
    scope: BuildTokenScope,
    audit: BuildTokenAudit,
    now: int,
) -> dict[str, Any]:
    """生成构建 token 的声明

    :param subject: 本次构建的唯一标识，代理据此在审计日志中追溯构建
    :param cluster_name: 构建所在集群名，镜像代理以此区分 audience
    :param ttl: 构建的超时时间（秒），token 在此基础上再保留 TOKEN_GRACE_SECONDS
    :param audit: 仅用于审计的声明，代理不据此授权
    :param now: 签发时刻，unix 秒
    :raises BuildTokenUnavailable: 集群名为空
    """
    if not cluster_name:
        raise BuildTokenUnavailable("cluster name is empty")

    return {
        **audit.to_claims(),
        "iss": ISSUER,
        "aud": AUDIENCE_PREFIX + cluster_name,
        "sub": subject,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + ttl + TOKEN_GRACE_SECONDS,
        "ver": CLAIMS_VERSION,
        "push": scope.push,
        "pull": scope.pull,
        "pull_deny": scope.pull_deny,
    }


def sign_build_token(claims: dict[str, Any], key: SigningKey) -> str:
    return jwt.encode(
        claims, key.to_pem().decode(), algorithm=SIGNING_ALGORITHM, headers={"kid": key.kid, "typ": "JWT"}
    )


def load_active_signing_key() -> SigningKey:
    """获取当前用于签发的密钥

    :raises BuildTokenUnavailable: 未配置签名密钥或配置非法
    """
    try:
        keyset = load_signing_key_set()
    except ImproperlyConfigured as e:
        # 上游错误只含下标、kid 和错误名，不含密钥内容，可以放进构建失败原因
        raise BuildTokenUnavailable(f"invalid build token signing key configuration: {e}") from None
    if not keyset:
        raise BuildTokenUnavailable("build token signing key is not configured")
    return keyset.active


def issue_token(
    *,
    subject: str,
    cluster_name: str,
    ttl: int,
    scope: BuildTokenScope,
    audit: BuildTokenAudit,
    now: int | None = None,
) -> str:
    """按授权范围签发构建 token。返回值等同于凭证，不得写入日志，参数含义见 make_build_token_claims

    :param now: 签发时刻，unix 秒，默认为当前时刻
    :raises BuildTokenUnavailable: 未配置签名密钥，或声明不满足签发条件
    """
    key = load_active_signing_key()
    claims = make_build_token_claims(
        subject=subject,
        cluster_name=cluster_name,
        ttl=ttl,
        scope=scope,
        audit=audit,
        now=int(time.time()) if now is None else now,
    )
    return sign_build_token(claims, key)


def issue_build_token(
    bp: "BuildProcess",
    metadata: "BuildMetadata",
    registry: "AppImageRegistry",
    cluster_name: str,
    now: int | None = None,
) -> str:
    """为应用模块构建签发构建 token。返回值等同于凭证，不得写入日志

    :param registry: 应用的平台仓库，即 `get_image_registry_by_app(bp.app)` 的返回值
    :param cluster_name: 应用所在集群名，即 `get_cluster_by_app(bp.app).name`
    :param now: 签发时刻，unix 秒，默认为当前时刻
    :raises BuildTokenUnavailable: 未配置签名密钥，或本次构建不满足签发条件
    """
    wl_app = bp.app
    return issue_token(
        # 统一为带连字符的 36 位格式
        subject=str(uuid.UUID(str(bp.uuid))),
        cluster_name=cluster_name,
        ttl=settings.BUILD_PROCESS_TIMEOUT,
        scope=make_module_build_scope(wl_app.paas_app_code, wl_app.module_name, metadata, registry),
        audit=BuildTokenAudit(app_code=wl_app.paas_app_code, module=wl_app.module_name),
        now=now,
    )
