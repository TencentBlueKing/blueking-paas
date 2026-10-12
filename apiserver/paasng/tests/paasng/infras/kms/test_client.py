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
import json

import pytest
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from paasng.infras.kms.client import CredentialInfo, KMSClient, KMSScope, ServiceAccountAuth
from paasng.infras.kms.constants import (
    AES_BLOCK_BITS,
    ERROR_CODE_RESOURCE_NOT_FOUND,
    K8S_SECRET_MAX_BYTES,
    PLAINTEXT_MAX_CHARS,
    SUPPORTED_CRYPTO_SUITE,
)
from paasng.infras.kms.exceptions import KMSAPIError, KMSCryptoError, KMSRequestError, KMSValidationError

NAME = "demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d"
AUTH = ServiceAccountAuth(name_list=("demo-web-prod-kms",), namespace_list=("ns-1",))


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


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


def _public_key_b64(private_key) -> str:
    pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(pem).decode("ascii")


def _crypto_info_data(private_key) -> dict:
    asymmetric, symmetric, mode = SUPPORTED_CRYPTO_SUITE
    return {
        "crypto": {"asymmetric_type": asymmetric, "symmetric_type": symmetric, "symmetric_mode": mode},
        "public_key": _public_key_b64(private_key),
    }


def _decrypt_envelope(envelope_b64: str, private_key) -> str:
    """按 bk-kms-sdk 的解密规则还原明文，用于验证 PaaS 侧生成的信封格式"""
    envelope = json.loads(base64.b64decode(envelope_b64))
    symmetric_key = private_key.decrypt(
        base64.b64decode(envelope["encrypted_key"]),
        asym_padding.OAEP(mgf=asym_padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    raw = base64.b64decode(envelope["ciphertext"])
    iv, body = raw[:16], raw[16:]
    decryptor = Cipher(algorithms.AES(symmetric_key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(body) + decryptor.finalize()
    unpadder = sym_padding.PKCS7(AES_BLOCK_BITS).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")


class TestEncryptCredentialValue:
    def test_envelope_decrypts_to_plaintext(self, client, rsa_key, monkeypatch):
        fake = FakeKMSRequest({"/api/v1/get/crypto_info": _crypto_info_data(rsa_key)})
        monkeypatch.setattr(client, "_request", fake)

        envelope = client.encrypt_credential_value("password-123")

        assert _decrypt_envelope(envelope, rsa_key) == "password-123"
        assert fake.calls == [("POST", "/api/v1/get/crypto_info", {"category": "normal"})]

    def test_envelope_has_expected_fields(self, client, rsa_key, monkeypatch):
        monkeypatch.setattr(
            client, "_request", FakeKMSRequest({"/api/v1/get/crypto_info": _crypto_info_data(rsa_key)})
        )

        envelope = json.loads(base64.b64decode(client.encrypt_credential_value("x")))

        assert set(envelope) == {"asymmetric_type", "symmetric_type", "symmetric_mode", "encrypted_key", "ciphertext"}

    def test_each_encryption_uses_fresh_key_material(self, client, rsa_key, monkeypatch):
        monkeypatch.setattr(
            client, "_request", FakeKMSRequest({"/api/v1/get/crypto_info": _crypto_info_data(rsa_key)})
        )

        assert client.encrypt_credential_value("same") != client.encrypt_credential_value("same")

    def test_rejects_plaintext_over_limit_without_calling_kms(self, client, monkeypatch):
        fake = FakeKMSRequest({})
        monkeypatch.setattr(client, "_request", fake)

        with pytest.raises(KMSValidationError):
            client.encrypt_credential_value("x" * (PLAINTEXT_MAX_CHARS + 1))
        assert fake.calls == []

    def test_rejects_unsupported_crypto_suite(self, client, rsa_key, monkeypatch):
        data = _crypto_info_data(rsa_key)
        data["crypto"]["symmetric_mode"] = "GCM"
        monkeypatch.setattr(client, "_request", FakeKMSRequest({"/api/v1/get/crypto_info": data}))

        with pytest.raises(KMSCryptoError):
            client.encrypt_credential_value("x")


class TestCreateCredentialFromEnvelope:
    def test_submits_envelope_with_encryption_flags(self, client, monkeypatch):
        fake = FakeKMSRequest({"/api/v1/credential": {"credential_id": 42}})
        monkeypatch.setattr(client, "_request", fake)

        credential_id = client.create_credential_from_envelope(
            scope=KMSScope(scope_id=7), name=NAME, envelope="ZW52ZWxvcGU=", auth=AUTH
        )

        assert credential_id == 42
        method, path, body = fake.calls[0]
        assert (method, path) == ("POST", "/api/v1/credential")
        assert body["scope"] == {"scope_type": "scope", "scope_id": 7}
        assert body["metadata"]["type"] == "secret"
        assert body["metadata"]["name"] == NAME
        assert body["metadata"]["alias_name"] == NAME
        assert body["metadata"]["value"] == "ZW52ZWxvcGU="
        assert body["metadata"]["enable_encrypt"] is True
        assert body["auth"] == {
            "service_account": {"name_list": ["demo-web-prod-kms"], "namespace_list": ["ns-1"]},
        }

    @pytest.mark.parametrize(
        "auth",
        [
            ServiceAccountAuth(name_list=("*",), namespace_list=("ns-1",)),
            ServiceAccountAuth(name_list=(), namespace_list=("ns-1",)),
            ServiceAccountAuth(name_list=("sa",), namespace_list=("*",)),
        ],
    )
    def test_rejects_wildcard_or_empty_authorization_before_request(self, client, monkeypatch, auth):
        fake = FakeKMSRequest({})
        monkeypatch.setattr(client, "_request", fake)

        with pytest.raises(KMSValidationError):
            client.create_credential_from_envelope(scope=KMSScope(scope_id=7), name=NAME, envelope="x", auth=auth)
        assert fake.calls == []

    @pytest.mark.parametrize("name", ["Bad.Name", "", "x" * 129])
    def test_rejects_invalid_name_before_request(self, client, monkeypatch, name):
        fake = FakeKMSRequest({})
        monkeypatch.setattr(client, "_request", fake)

        with pytest.raises(KMSValidationError):
            client.create_credential_from_envelope(scope=KMSScope(scope_id=7), name=name, envelope="x", auth=AUTH)
        assert fake.calls == []

    @pytest.mark.parametrize("envelope", ["", "A" * (K8S_SECRET_MAX_BYTES + 1)])
    def test_rejects_empty_or_oversized_envelope_before_request(self, client, monkeypatch, envelope):
        fake = FakeKMSRequest({})
        monkeypatch.setattr(client, "_request", fake)

        with pytest.raises(KMSValidationError):
            client.create_credential_from_envelope(scope=KMSScope(scope_id=7), name=NAME, envelope=envelope, auth=AUTH)
        assert fake.calls == []


class TestEncryptThenCreate:
    def test_submits_encrypted_value_without_plaintext(self, client, rsa_key, monkeypatch):
        fake = FakeKMSRequest(
            {
                "/api/v1/get/crypto_info": _crypto_info_data(rsa_key),
                "/api/v1/credential": {"credential_id": 5},
            }
        )
        monkeypatch.setattr(client, "_request", fake)

        envelope = client.encrypt_credential_value("hello")
        credential_id = client.create_credential_from_envelope(
            scope=KMSScope(scope_id=7), name=NAME, envelope=envelope, auth=AUTH
        )

        assert credential_id == 5
        submitted = fake.calls[-1][2]["metadata"]["value"]
        assert submitted == envelope
        assert _decrypt_envelope(submitted, rsa_key) == "hello"
        assert "hello" not in json.dumps(fake.calls[-1][2])


class TestFindCredential:
    def test_returns_none_when_not_found(self, client, monkeypatch):
        not_found = KMSAPIError(ERROR_CODE_RESOURCE_NOT_FOUND, "not found")
        monkeypatch.setattr(client, "_request", FakeKMSRequest({"/api/v1/get/credential": not_found}))

        assert client.find_credential(scope=KMSScope(scope_id=7), name=NAME) is None

    def test_parses_metadata_and_authorization(self, client, monkeypatch):
        data = {
            "metadata": {"credential_id": 9, "name": NAME, "enable_encrypt": True},
            "scope": {"scope_id": 7, "scope_type": "scope"},
            "auth": {"service_account": {"name_list": ["demo-web-prod-kms"], "namespace_list": ["ns-1"]}},
        }
        fake = FakeKMSRequest({"/api/v1/get/credential": data})
        monkeypatch.setattr(client, "_request", fake)

        info = client.find_credential(scope=KMSScope(scope_id=7), name=NAME)

        assert info == CredentialInfo(
            credential_id=9,
            scope=KMSScope(scope_id=7),
            name=NAME,
            enable_encrypt=True,
            auth=AUTH,
        )
        assert fake.calls[0][2] == {"scope": {"scope_type": "scope", "scope_id": 7}, "type": "secret", "name": NAME}

    def test_missing_authorization_is_reported_as_wildcard(self, client, monkeypatch):
        data = {
            "metadata": {"credential_id": 9, "name": NAME, "enable_encrypt": True},
            "scope": {"scope_id": 7, "scope_type": "scope"},
        }
        monkeypatch.setattr(client, "_request", FakeKMSRequest({"/api/v1/get/credential": data}))

        info = client.find_credential(scope=KMSScope(scope_id=7), name=NAME)

        assert info is not None
        assert info.auth == ServiceAccountAuth(name_list=("*",), namespace_list=("*",))


class TestDeleteCredential:
    def test_sends_credential_id(self, client, monkeypatch):
        fake = FakeKMSRequest({"/api/v1/credential": {}})
        monkeypatch.setattr(client, "_request", fake)

        client.delete_credential(9)

        assert fake.calls == [("DELETE", "/api/v1/credential", {"credential_id": 9})]


class TestScopeValidation:
    @pytest.mark.parametrize("scope_id", [0, -1])
    def test_scope_id_must_be_positive(self, scope_id):
        with pytest.raises(KMSValidationError):
            KMSScope(scope_id=scope_id)


class TestRequestErrorMapping:
    def test_success_returns_data(self, client, monkeypatch):
        session = FakeSession(FakeResponse(200, {"code": 0, "data": {"credential_id": 1}}))
        monkeypatch.setattr(client, "_session", session)

        assert client._request("POST", "/api/v1/credential", {}) == {"credential_id": 1}
        assert session.sent[0]["url"] == "http://kms.example/api/v1/credential"
        assert session.sent[0]["timeout"] == 5

    def test_business_error_is_api_error_even_with_http_200(self, client, monkeypatch):
        monkeypatch.setattr(
            client,
            "_session",
            FakeSession(FakeResponse(200, {"code": ERROR_CODE_RESOURCE_NOT_FOUND, "message": "not found"})),
        )

        with pytest.raises(KMSAPIError) as exc_info:
            client._request("POST", "/api/v1/get/credential", {})
        assert exc_info.value.code == ERROR_CODE_RESOURCE_NOT_FOUND

    def test_business_error_is_api_error_with_http_500(self, client, monkeypatch):
        monkeypatch.setattr(client, "_session", FakeSession(FakeResponse(500, {"code": 1000001, "message": "boom"})))

        with pytest.raises(KMSAPIError):
            client._request("POST", "/api/v1/credential", {})

    def test_http_error_without_business_body_is_request_error(self, client, monkeypatch):
        monkeypatch.setattr(client, "_session", FakeSession(FakeResponse(502, json_error=True)))

        with pytest.raises(KMSRequestError) as exc_info:
            client._request("POST", "/api/v1/credential", {})
        assert exc_info.value.status_code == 502

    def test_transport_error_is_request_error(self, client, monkeypatch):
        monkeypatch.setattr(client, "_session", FakeSession(error=requests.ConnectionError("refused")))

        with pytest.raises(KMSRequestError):
            client._request("POST", "/api/v1/credential", {})

    def test_success_without_code_is_request_error(self, client, monkeypatch):
        monkeypatch.setattr(client, "_session", FakeSession(FakeResponse(200, {"message": "no code"})))

        with pytest.raises(KMSRequestError):
            client._request("POST", "/api/v1/credential", {})
