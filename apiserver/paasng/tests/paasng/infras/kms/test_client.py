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

import base64

import bk_kms
import pytest
import requests
from bkcrypto.asymmetric.ciphers.sm2 import SM2AsymmetricCipher
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from paasng.infras.kms.client import CredentialInfo, KMSClient, KMSScope, ServiceAccountAuth
from paasng.infras.kms.constants import ERROR_CODE_RESOURCE_NOT_FOUND, K8S_SECRET_MAX_BYTES, PLAINTEXT_MAX_CHARS
from paasng.infras.kms.exceptions import KMSAPIError, KMSCryptoError, KMSRequestError, KMSValidationError

NAME = "demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d"
SCOPE = KMSScope(scope_id=7)
AUTH = ServiceAccountAuth(name_list=("demo-web-prod-kms",), namespace_list=("ns-1",))


def _b64(text: str | bytes) -> str:
    return base64.b64encode(text.encode() if isinstance(text, str) else text).decode("ascii")


@pytest.fixture(scope="module")
def key_pairs() -> dict[str, tuple[str, str]]:
    """各非对称算法的（KMS 下发的公钥，应用端 SDK 使用的私钥），均为 Base64 编码的 PEM"""
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_public = rsa_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    rsa_private = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    sm2 = SM2AsymmetricCipher()
    return {
        "RSA": (_b64(rsa_public), _b64(rsa_private)),
        "SM2": (_b64(sm2.export_public_key()), _b64(sm2.export_private_key())),
    }


def _crypto_info_data(key_pairs, asymmetric_type="RSA", symmetric_type="AES", symmetric_mode="CBC") -> dict:
    return {
        "crypto": {
            "asymmetric_type": asymmetric_type,
            "symmetric_type": symmetric_type,
            "symmetric_mode": symmetric_mode,
        },
        "public_key": key_pairs[asymmetric_type][0],
    }


@pytest.fixture
def client():
    return KMSClient(base_url="http://kms.example", username="paas", tenant_id="default", timeout=5)


class FakeKMSRequest:
    """替代 KMSClient._request：记录每次调用，并按路径返回预设结果（异常会被抛出）"""

    def __init__(self, responses: dict):
        self.responses = responses
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, method: str, path: str, body: dict) -> dict:
        self.calls.append((method, path, body))
        response = self.responses[path]
        if isinstance(response, Exception):
            raise response
        return response


class FakeResponse:
    def __init__(self, status_code: int, payload=None, *, json_error: bool = False):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("not json")
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.sent: list[dict] = []

    def request(self, method, url, json=None, timeout=None):
        self.sent.append({"method": method, "url": url, "json": json, "timeout": timeout})
        if self.error is not None:
            raise self.error
        return self.response


class TestEncryptCredentialValue:
    @pytest.mark.parametrize("asymmetric_type", ["RSA", "SM2"])
    @pytest.mark.parametrize("symmetric_type", ["AES", "SM4"])
    @pytest.mark.parametrize("symmetric_mode", ["CBC", "CTR"])
    def test_envelope_decrypts_with_app_sdk(
        self, client, key_pairs, monkeypatch, asymmetric_type, symmetric_type, symmetric_mode
    ):
        data = _crypto_info_data(key_pairs, asymmetric_type, symmetric_type, symmetric_mode)
        fake = FakeKMSRequest({"/api/v1/get/crypto_info": data})
        monkeypatch.setattr(client, "_request", fake)

        envelope = client.encrypt_credential_value('{"DB_PASSWORD": "密码-123"}')

        sdk_private_key = key_pairs[asymmetric_type][1]
        assert bk_kms.decrypt(envelope, sdk_private_key) == '{"DB_PASSWORD": "密码-123"}'
        assert fake.calls == [("POST", "/api/v1/get/crypto_info", {"category": "normal"})]

    def test_each_encryption_uses_fresh_key_material(self, client, key_pairs, monkeypatch):
        monkeypatch.setattr(
            client, "_request", FakeKMSRequest({"/api/v1/get/crypto_info": _crypto_info_data(key_pairs)})
        )

        assert client.encrypt_credential_value("same") != client.encrypt_credential_value("same")

    def test_rejects_plaintext_over_limit_without_calling_kms(self, client, monkeypatch):
        fake = FakeKMSRequest({})
        monkeypatch.setattr(client, "_request", fake)

        with pytest.raises(KMSValidationError):
            client.encrypt_credential_value("x" * (PLAINTEXT_MAX_CHARS + 1))
        assert fake.calls == []

    def test_rejects_unsupported_crypto_suite(self, client, key_pairs, monkeypatch):
        data = _crypto_info_data(key_pairs, symmetric_mode="GCM")
        monkeypatch.setattr(client, "_request", FakeKMSRequest({"/api/v1/get/crypto_info": data}))

        with pytest.raises(KMSCryptoError):
            client.encrypt_credential_value("x")

    def test_rejects_public_key_of_another_algorithm(self, client, key_pairs, monkeypatch):
        data = _crypto_info_data(key_pairs)
        data["public_key"] = key_pairs["SM2"][0]
        monkeypatch.setattr(client, "_request", FakeKMSRequest({"/api/v1/get/crypto_info": data}))

        with pytest.raises(KMSCryptoError):
            client.encrypt_credential_value("x")


class TestCreateCredentialFromEnvelope:
    def test_submits_envelope_with_encryption_flags(self, client, monkeypatch):
        fake = FakeKMSRequest({"/api/v1/credential": {"credential_id": 42}})
        monkeypatch.setattr(client, "_request", fake)

        credential_id = client.create_credential_from_envelope(
            scope=SCOPE, name=NAME, envelope="ZW52ZWxvcGU=", auth=AUTH
        )

        assert credential_id == 42
        method, path, body = fake.calls[0]
        assert (method, path) == ("POST", "/api/v1/credential")
        assert body["scope"] == {"scope_type": "scope", "scope_id": 7}
        assert body["metadata"]["type"] == "secret"
        assert body["metadata"]["name"] == NAME
        assert body["metadata"]["value"] == "ZW52ZWxvcGU="
        assert body["metadata"]["enable_encrypt"] is True
        assert body["auth"] == {
            "service_account": {"name_list": ["demo-web-prod-kms"], "namespace_list": ["ns-1"]},
        }

    @pytest.mark.parametrize(
        ("auth", "envelope"),
        [
            (ServiceAccountAuth(name_list=("*",), namespace_list=("ns-1",)), "x"),
            (ServiceAccountAuth(name_list=(), namespace_list=("ns-1",)), "x"),
            (ServiceAccountAuth(name_list=("sa",), namespace_list=("*",)), "x"),
            (AUTH, ""),
            (AUTH, "A" * (K8S_SECRET_MAX_BYTES + 1)),
        ],
    )
    def test_rejects_invalid_input_before_request(self, client, monkeypatch, auth, envelope):
        fake = FakeKMSRequest({})
        monkeypatch.setattr(client, "_request", fake)

        with pytest.raises(KMSValidationError):
            client.create_credential_from_envelope(scope=SCOPE, name=NAME, envelope=envelope, auth=auth)
        assert fake.calls == []


class TestFindCredential:
    def test_returns_none_when_not_found(self, client, monkeypatch):
        not_found = KMSAPIError(ERROR_CODE_RESOURCE_NOT_FOUND, "not found")
        monkeypatch.setattr(client, "_request", FakeKMSRequest({"/api/v1/get/credential": not_found}))

        assert client.find_credential(scope=SCOPE, name=NAME) is None

    def test_parses_metadata_and_authorization(self, client, monkeypatch):
        data = {
            "metadata": {"credential_id": 9, "name": NAME, "enable_encrypt": True},
            "scope": {"scope_id": 7, "scope_type": "scope"},
            "auth": {"service_account": {"name_list": ["demo-web-prod-kms"], "namespace_list": ["ns-1"]}},
        }
        fake = FakeKMSRequest({"/api/v1/get/credential": data})
        monkeypatch.setattr(client, "_request", fake)

        info = client.find_credential(scope=SCOPE, name=NAME)

        assert info == CredentialInfo(credential_id=9, scope=SCOPE, name=NAME, enable_encrypt=True, auth=AUTH)
        assert fake.calls[0][2] == {"scope": {"scope_type": "scope", "scope_id": 7}, "type": "secret", "name": NAME}

    def test_missing_authorization_is_reported_as_wildcard(self, client, monkeypatch):
        data = {
            "metadata": {"credential_id": 9, "name": NAME, "enable_encrypt": True},
            "scope": {"scope_id": 7, "scope_type": "scope"},
        }
        monkeypatch.setattr(client, "_request", FakeKMSRequest({"/api/v1/get/credential": data}))

        info = client.find_credential(scope=SCOPE, name=NAME)

        assert info is not None
        assert info.auth == ServiceAccountAuth(name_list=("*",), namespace_list=("*",))


class TestRequest:
    def test_success_returns_data(self, client, monkeypatch):
        session = FakeSession(FakeResponse(200, {"code": 0, "data": {"credential_id": 1}}))
        monkeypatch.setattr(client, "_session", session)

        assert client._request("POST", "/api/v1/credential", {}) == {"credential_id": 1}
        assert session.sent[0]["url"] == "http://kms.example/api/v1/credential"
        assert session.sent[0]["timeout"] == 5

    @pytest.mark.parametrize(
        ("session", "exc_type"),
        [
            # 业务错误以响应中的 code 为准，与 HTTP 状态码无关
            (FakeSession(FakeResponse(200, {"code": ERROR_CODE_RESOURCE_NOT_FOUND, "message": "x"})), KMSAPIError),
            (FakeSession(FakeResponse(500, {"code": 1000001, "message": "boom"})), KMSAPIError),
            (FakeSession(FakeResponse(502, json_error=True)), KMSRequestError),
            (FakeSession(FakeResponse(200, {"message": "no code"})), KMSRequestError),
            (FakeSession(error=requests.ConnectionError("refused")), KMSRequestError),
        ],
    )
    def test_error_mapping(self, client, monkeypatch, session, exc_type):
        monkeypatch.setattr(client, "_session", session)

        with pytest.raises(exc_type):
            client._request("POST", "/api/v1/credential", {})
