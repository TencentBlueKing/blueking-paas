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
import datetime
import json
import ssl
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import bk_kms
import pytest
import requests
from bkcrypto.asymmetric.ciphers.sm2 import SM2AsymmetricCipher
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.test import override_settings

from paasng.infras.kms.client import CredentialInfo, KMSClient, KMSScope, ServiceAccountAuth, make_kms_client
from paasng.infras.kms.constants import ERROR_CODE_RESOURCE_NOT_FOUND, K8S_SECRET_MAX_BYTES, PLAINTEXT_MAX_CHARS
from paasng.infras.kms.exceptions import (
    KMSAPIError,
    KMSConfigError,
    KMSCryptoError,
    KMSRequestError,
    KMSValidationError,
)

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

    def request(self, method, url, json=None, timeout=None):
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
        monkeypatch.setattr(client, "_session", FakeSession(FakeResponse(200, {"code": 0, "data": data})))

        info = client.find_credential(scope=SCOPE, name=NAME)

        assert info == CredentialInfo(credential_id=9, scope=SCOPE, name=NAME, enable_encrypt=True, auth=AUTH)

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


def _issue_cert(
    subject: str, key: rsa.RSAPrivateKey, ca_key: rsa.RSAPrivateKey, san: str | None = None
) -> x509.Certificate:
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "kms-ca")]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
    )
    if key is ca_key:
        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    if san:
        builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName(san)]), critical=False)
    return builder.sign(ca_key, hashes.SHA256())


@pytest.fixture(scope="module")
def pki(tmp_path_factory) -> Path:
    """CA 与运维提供的一样不带 Key Usage 扩展，Python 3.13+ 的 ssl.create_default_context 会拒绝它"""
    directory = tmp_path_factory.mktemp("kms-tls")
    pem = serialization.Encoding.PEM
    ca_key, server_key, client_key = (rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(3))
    (directory / "ca.crt").write_bytes(_issue_cert("kms-ca", ca_key, ca_key).public_bytes(pem))
    (directory / "server.crt").write_bytes(_issue_cert("kms", server_key, ca_key, san="localhost").public_bytes(pem))
    (directory / "client.crt").write_bytes(_issue_cert("bkpaas3-saas", client_key, ca_key).public_bytes(pem))
    for name, key, encryption in [
        ("server.key", server_key, serialization.NoEncryption()),
        ("client.key", client_key, serialization.NoEncryption()),
        ("client.enc.key", client_key, serialization.BestAvailableEncryption(b"secret")),
    ]:
        (directory / name).write_bytes(
            key.private_bytes(pem, serialization.PrivateFormat.TraditionalOpenSSL, encryption)
        )
    return directory


@pytest.fixture(scope="module")
def mtls_port(pki) -> Iterator[int]:
    """要求客户端证书的 KMS 服务，在 crypto_info 响应的 public_key 字段中回显客户端证书的 CN"""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            subject = dict(item[0] for item in self.connection.getpeercert()["subject"])
            crypto = {"asymmetric_type": "RSA", "symmetric_type": "AES", "symmetric_mode": "CBC"}
            body = json.dumps({"code": 0, "data": {"crypto": crypto, "public_key": subject["commonName"]}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(pki / "server.crt", pki / "server.key")
    context.load_verify_locations(pki / "ca.crt")
    context.verify_mode = ssl.CERT_REQUIRED
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


def _tls_settings(pki: Path, base_url: str, key_file: str = "client.key"):
    return override_settings(
        KMS_API_BASE_URL=base_url,
        KMS_API_USERNAME="paas",
        KMS_API_TLS_CA_FILE=str(pki / "ca.crt"),
        KMS_API_TLS_CERT_FILE=str(pki / "client.crt"),
        KMS_API_TLS_KEY_FILE=str(pki / key_file) if key_file else "",
        KMS_API_TLS_CHECK_HOSTNAME=True,
    )


class TestMutualTLS:
    def test_presents_client_certificate(self, pki, mtls_port):
        with _tls_settings(pki, f"https://localhost:{mtls_port}"):
            info = make_kms_client("default").get_crypto_info()

        assert info.public_key == "bkpaas3-saas"

    def test_ignores_requests_ca_bundle_env(self, pki, mtls_port, monkeypatch):
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(pki / "nonexistent.crt"))

        with _tls_settings(pki, f"https://localhost:{mtls_port}"):
            assert make_kms_client("default").get_crypto_info().public_key == "bkpaas3-saas"

    @pytest.mark.parametrize(
        ("base_url", "key_file"),
        [
            ("http://localhost", "client.key"),
            ("https://localhost", ""),
            ("https://localhost", "client.enc.key"),
        ],
    )
    def test_invalid_config(self, pki, base_url, key_file):
        with _tls_settings(pki, base_url, key_file), pytest.raises(KMSConfigError):
            make_kms_client("default")
