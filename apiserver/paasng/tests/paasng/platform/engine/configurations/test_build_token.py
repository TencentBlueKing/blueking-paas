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

import json
import logging
import os
import stat
import uuid
from io import StringIO
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError

from paas_wl.bk_app.applications.entities import BuildMetadata
from paas_wl.infras.cluster.entities import AppImageRegistry
from paasng.platform.engine.configurations.build_token import (
    BuildTokenUnavailable,
    SigningKey,
    SigningKeySet,
    issue_build_token,
    load_signing_key_set,
    make_upstream_alias,
)

HOST = "example.com"
ALIAS = "example-com"
NAMESPACE = "bkpaas/docker"
APP_CODE = "demo"
MODULE = "default"
CLUSTER = "default-main"
TAG = "main-3f2a1bc"
REPO = f"{HOST}/{NAMESPACE}/{APP_CODE}/{MODULE}"
CLIENT_REPO = f"{ALIAS}/{NAMESPACE}/{APP_CODE}/{MODULE}"
TIMEOUT = 900


def _pem(key: SigningKey) -> str:
    return key.to_pem().decode()


def _registry(host: str = HOST, namespace: str = NAMESPACE) -> AppImageRegistry:
    return AppImageRegistry(
        host=host, skip_tls_verify=False, namespace=namespace, username="bkpaas", password="platform-secret"
    )


def _kaniko_metadata(image: str = f"{REPO}:{TAG}") -> BuildMetadata:
    return BuildMetadata(image=image, image_repository=REPO, use_dockerfile=True)


def _cnb_metadata(image: str = f"{REPO}:{TAG}") -> BuildMetadata:
    return BuildMetadata(image=image, image_repository=REPO, use_cnb=True)


def _load_keyset() -> SigningKeySet:
    keyset = load_signing_key_set()
    assert keyset is not None
    return keyset


def _verify(token: str, jwks: dict) -> dict:
    """用 JWKS 校验 token，返回声明"""
    kid = jwt.get_unverified_header(token)["kid"]
    jwk = next(k for k in jwks["keys"] if k["kid"] == kid)
    return jwt.decode(
        token,
        jwt.PyJWK(jwk).key,
        algorithms=["EdDSA"],
        audience=f"bkpaas-registry-proxy:{CLUSTER}",
        issuer="bkpaas-apiserver",
        leeway=30,
        options={"require": ["exp", "iat", "sub", "jti"]},
    )


@pytest.fixture()
def signing_key() -> SigningKey:
    return SigningKey.generate()


@pytest.fixture()
def _with_signing_key(settings, signing_key):
    settings.BUILD_TOKEN_SIGNING_KEYS = [_pem(signing_key)]
    settings.BUILD_TOKEN_ACTIVE_KID = ""
    settings.BUILD_PROCESS_TIMEOUT = TIMEOUT


@pytest.fixture()
def build_proc() -> SimpleNamespace:
    """只提供签发所需字段的 BuildProcess"""
    return SimpleNamespace(uuid=uuid.uuid4(), app=SimpleNamespace(paas_app_code=APP_CODE, module_name=MODULE))


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("example.com", "example-com"),
        ("registry.local:5000", "registry-local-5000"),
        ("Registry.Local", "registry-local"),
    ],
)
def test_make_upstream_alias(host, expected):
    assert make_upstream_alias(host) == expected


@pytest.mark.parametrize("host", ["", "[::1]:5000", "https://example.com", "example.com/", "-a.com"])
def test_make_upstream_alias_invalid(host):
    with pytest.raises(ValueError, match="upstream alias"):
        make_upstream_alias(host)


class TestSigningKey:
    def test_public_jwk_has_no_private_member(self, signing_key):
        jwk = signing_key.public_jwk()

        assert jwk == {
            "kty": "OKP",
            "crv": "Ed25519",
            "x": signing_key.x,
            "kid": signing_key.kid,
            "alg": "EdDSA",
            "use": "sig",
        }
        assert _pem(signing_key) not in repr(signing_key)


class TestLoadSigningKeySet:
    def test_not_configured(self, settings):
        settings.BUILD_TOKEN_SIGNING_KEYS = []
        settings.BUILD_TOKEN_ACTIVE_KID = ""
        assert load_signing_key_set() is None

    @pytest.mark.parametrize("as_string", [False, True])
    def test_single_key(self, settings, signing_key, as_string):
        """单把密钥配成列表；通过环境变量配置时 dynaconf 读到的是字符串"""
        pem = _pem(signing_key)
        settings.BUILD_TOKEN_SIGNING_KEYS = pem if as_string else [pem]
        settings.BUILD_TOKEN_ACTIVE_KID = ""
        assert _load_keyset().active.kid == signing_key.kid

    def test_multiple_keys_with_active_kid(self, settings, signing_key):
        new_key = SigningKey.generate()
        settings.BUILD_TOKEN_SIGNING_KEYS = [_pem(signing_key), _pem(new_key)]
        settings.BUILD_TOKEN_ACTIVE_KID = new_key.kid

        keyset = _load_keyset()

        assert keyset.active.kid == new_key.kid
        assert [k["kid"] for k in keyset.to_jwks()["keys"]] == [signing_key.kid, new_key.kid]

    @pytest.mark.parametrize(
        ("keys", "active_kid", "error"),
        [
            ("two", "", "BUILD_TOKEN_ACTIVE_KID is required"),
            ("two", "unknown-kid", "not found"),
            ("duplicated", "", "duplicated"),
            ("none", "some-kid", "BUILD_TOKEN_SIGNING_KEYS is empty"),
            ("not_list", "", "must be a list"),
            ("not_ed25519", "", "not an Ed25519 private key"),
        ],
    )
    def test_invalid_config(self, settings, signing_key, keys, active_kid, error):
        ec_pem = ec.generate_private_key(ec.SECP256R1()).private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        settings.BUILD_TOKEN_SIGNING_KEYS = {
            "two": [_pem(signing_key), _pem(SigningKey.generate())],
            "duplicated": [_pem(signing_key), _pem(signing_key)],
            "none": [],
            "not_list": {"key": _pem(signing_key)},
            "not_ed25519": [ec_pem.decode()],
        }[keys]
        settings.BUILD_TOKEN_ACTIVE_KID = active_kid

        with pytest.raises(ImproperlyConfigured, match=error):
            load_signing_key_set()


@pytest.mark.usefixtures("_with_signing_key")
class TestIssueBuildToken:
    def test_kaniko(self, build_proc, signing_key):
        """Dockerfile 构建的 token 仅授权本应用产物（具体 tag）与缓存仓库"""
        token = issue_build_token(build_proc, _kaniko_metadata(), _registry(), CLUSTER)

        header = jwt.get_unverified_header(token)
        assert header == {"alg": "EdDSA", "kid": signing_key.kid, "typ": "JWT"}

        claims = _verify(token, _load_keyset().to_jwks())
        assert claims["push"] == [
            {"repo": CLIENT_REPO, "tags": [TAG]},
            {"repo": f"{CLIENT_REPO}/dockerbuild-cache", "tags": ["*"]},
        ]
        assert claims["sub"] == str(build_proc.uuid)
        assert len(claims["sub"]) == 36
        assert claims["exp"] - claims["iat"] == TIMEOUT + 300
        assert claims["ver"] == 1
        assert claims["app_code"] == APP_CODE
        assert claims["module"] == MODULE
        assert len(claims["jti"]) == 32
        assert set(claims) == {
            "iss",
            "aud",
            "sub",
            "jti",
            "iat",
            "exp",
            "ver",
            "app_code",
            "module",
            "push",
            "pull",
            "pull_deny",
        }

    def test_cnb(self, build_proc):
        """AC-T06：buildpack 构建的缓存是产物仓库中的 tag，不使用 "*" """
        claims = _verify(
            issue_build_token(build_proc, _cnb_metadata(), _registry(), CLUSTER), _load_keyset().to_jwks()
        )
        assert claims["push"] == [{"repo": CLIENT_REPO, "tags": [TAG, "cnb-build-cache"]}]

    def test_pull_scope(self, build_proc):
        """AC-T05：平台仓库中仅本应用产物与缓存可读，其他应用不可读"""
        claims = _verify(
            issue_build_token(build_proc, _kaniko_metadata(), _registry(), CLUSTER), _load_keyset().to_jwks()
        )
        assert claims["pull"] == [f"{ALIAS}/"]
        assert claims["pull_deny"] == [f"{ALIAS}/{NAMESPACE}/"]

    def test_registry_with_port(self, build_proc):
        image = f"registry.local:5000/{NAMESPACE}/{APP_CODE}/{MODULE}:{TAG}"
        claims = _verify(
            issue_build_token(build_proc, _kaniko_metadata(image), _registry(host="registry.local:5000"), CLUSTER),
            _load_keyset().to_jwks(),
        )
        assert claims["push"][0]["repo"] == f"registry-local-5000/{NAMESPACE}/{APP_CODE}/{MODULE}"

    def test_rotation(self, settings, build_proc, signing_key):
        """新旧两把密钥签发的 token 都能被导出的 JWKS 校验"""
        new_key = SigningKey.generate()
        settings.BUILD_TOKEN_SIGNING_KEYS = [_pem(signing_key), _pem(new_key)]

        tokens = []
        for kid in [signing_key.kid, new_key.kid]:
            settings.BUILD_TOKEN_ACTIVE_KID = kid
            tokens.append(issue_build_token(build_proc, _kaniko_metadata(), _registry(), CLUSTER))

        jwks = _load_keyset().to_jwks()
        assert [jwt.get_unverified_header(t)["kid"] for t in tokens] == [signing_key.kid, new_key.kid]
        for token in tokens:
            assert _verify(token, jwks)["sub"] == str(build_proc.uuid)

        exported = json.dumps(jwks)
        assert '"d"' not in exported
        for key in [signing_key, new_key]:
            assert key.to_pem().decode().splitlines()[1] not in exported

    def test_no_secret_in_logs(self, caplog, build_proc, signing_key):
        with caplog.at_level(logging.DEBUG):
            load_signing_key_set()
            token = issue_build_token(build_proc, _kaniko_metadata(), _registry(), CLUSTER)

        assert signing_key.to_pem().decode().splitlines()[1] not in caplog.text
        assert token not in caplog.text


class TestIssueBuildTokenUnavailable:
    def test_invalid_signing_key(self, settings, build_proc):
        settings.BUILD_TOKEN_SIGNING_KEYS = ["not a pem"]
        settings.BUILD_TOKEN_ACTIVE_KID = ""

        with pytest.raises(BuildTokenUnavailable, match="invalid build token signing key configuration") as exc_info:
            issue_build_token(build_proc, _kaniko_metadata(), _registry(), CLUSTER)
        assert "BUILD_TOKEN_SIGNING_KEYS[0] is invalid" in str(exc_info.value)
        assert "not a pem" not in str(exc_info.value)

    @pytest.mark.usefixtures("_with_signing_key")
    @pytest.mark.parametrize(
        ("metadata", "registry", "cluster_name", "error"),
        [
            (_kaniko_metadata(), _registry(host=""), CLUSTER, "host or namespace is empty"),
            (_kaniko_metadata(), _registry(namespace=""), CLUSTER, "host or namespace is empty"),
            (_kaniko_metadata(), _registry(namespace="bkpaas/"), CLUSTER, "invalid platform image registry namespace"),
            (_kaniko_metadata(), _registry(host="[::1]:5000"), CLUSTER, "cannot derive an upstream alias"),
            (_kaniko_metadata(), _registry(), "", "cluster name is empty"),
            # 产物不在本应用本模块的仓库中
            (
                _kaniko_metadata(f"{HOST}/{NAMESPACE}/other-app/{MODULE}:{TAG}"),
                _registry(),
                CLUSTER,
                "does not belong",
            ),
            (
                _kaniko_metadata(f"{HOST}/{NAMESPACE}/{APP_CODE}/{MODULE}/x:{TAG}"),
                _registry(),
                CLUSTER,
                "does not belong",
            ),
            (_kaniko_metadata(REPO), _registry(), CLUSTER, "does not belong"),
            (_kaniko_metadata(f"{REPO}@sha256:{'0' * 64}"), _registry(), CLUSTER, "does not belong"),
            (
                BuildMetadata(image=f"{REPO}:{TAG}"),
                _registry(),
                CLUSTER,
                "only supported for Dockerfile and buildpack",
            ),
        ],
    )
    def test_invalid_build(self, build_proc, metadata, registry, cluster_name, error):
        with pytest.raises(BuildTokenUnavailable, match=error) as exc_info:
            issue_build_token(build_proc, metadata, registry, cluster_name)
        assert str(exc_info.value).startswith("image credential unavailable: ")


class TestCommands:
    def test_generate_signing_key(self, tmp_path):
        path = tmp_path / "k1.pem"
        out = StringIO()

        call_command("generate_build_token_signing_key", output=str(path), stdout=out)

        key = SigningKey.from_pem(path.read_bytes())
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
        assert key.kid in out.getvalue()
        assert "PRIVATE KEY" not in out.getvalue()

    def test_generate_signing_key_refuses_overwrite(self, tmp_path):
        path = tmp_path / "k1.pem"
        path.write_text("existing")

        with pytest.raises(CommandError, match="already exists"):
            call_command("generate_build_token_signing_key", output=str(path), stdout=StringIO())
        assert path.read_text() == "existing"

    def test_export_jwks(self, settings, tmp_path, signing_key):
        new_key = SigningKey.generate()
        settings.BUILD_TOKEN_SIGNING_KEYS = [_pem(signing_key), _pem(new_key)]
        settings.BUILD_TOKEN_ACTIVE_KID = signing_key.kid
        path = tmp_path / "jwks.json"
        err = StringIO()

        call_command("export_build_token_jwks", output=str(path), stdout=StringIO(), stderr=err)

        jwks = json.loads(path.read_text())
        assert jwks == {"keys": [signing_key.public_jwk(), new_key.public_jwk()]}
        assert f"active kid: {signing_key.kid}" in err.getvalue()
        assert "PRIVATE KEY" not in path.read_text() + err.getvalue()

    def test_export_jwks_not_configured(self, settings):
        settings.BUILD_TOKEN_SIGNING_KEYS = []
        settings.BUILD_TOKEN_ACTIVE_KID = ""

        with pytest.raises(CommandError, match="not configured"):
            call_command("export_build_token_jwks", stdout=StringIO())
