# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

import datetime
import pathlib
import random
import socket
import ssl
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from unittest import mock

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from paasng.utils.moby_distribution.spec.endpoint import APIEndpoint


def get_server_address():
    return "localhost", random.randint(10000, 40000)


@pytest.fixture()
def certfile(tmp_path: pathlib.Path):
    """generate a self-signed certificate"""
    one_day = datetime.timedelta(1, 0, 0)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())

    public_key = private_key.public_key()
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(
        x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ]
        )
    )
    builder = builder.issuer_name(
        x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ]
        )
    )
    builder = builder.not_valid_before(datetime.datetime.today() - one_day)
    builder = builder.not_valid_after(datetime.datetime.today() + (one_day * 30))
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(public_key)
    builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
    builder = builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    )
    certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256(), backend=default_backend())
    certificate_path = tmp_path / "certificate"
    certificate_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        + b"\n"
        + certificate.public_bytes(serialization.Encoding.PEM)
    )

    yield certificate_path
    certificate_path.unlink()


@pytest.fixture()
def httpd():
    server_address = get_server_address()
    for _ in range(10):
        try:
            with HTTPServer(server_address, SimpleHTTPRequestHandler) as httpd:
                yield httpd
                break
        except OSError:
            continue
    else:
        pytest.skip("failed to start http server")


@pytest.fixture()
def http_server(httpd):
    sa = httpd.socket.getsockname()
    t = threading.Thread(target=httpd.serve_forever)
    t.start()
    yield sa[0], sa[1]
    httpd.shutdown()


@pytest.fixture()
def https_server(httpd, certfile):
    httpd.socket = ssl.wrap_socket(httpd.socket, server_side=True, ssl_version=ssl.PROTOCOL_TLS, certfile=certfile)
    sa = httpd.socket.getsockname()
    t = threading.Thread(target=httpd.serve_forever)
    t.start()
    yield sa[0], sa[1]
    httpd.shutdown()


@pytest.fixture()
def blocking_https_server(httpd, certfile):
    """start a not running https server, will always block every request"""
    httpd.socket = ssl.wrap_socket(httpd.socket, server_side=True, ssl_version=ssl.PROTOCOL_TLS, certfile=certfile)
    sa = httpd.socket.getsockname()
    # t = threading.Thread(target=httpd.serve_forever)
    # t.start()
    return sa[0], sa[1]
    # httpd.shutdown()


@pytest.fixture()
def server(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize(
    ("server", "expected"),
    [
        ("http_server", (False, False)),
        ("https_server", (True, False)),
    ],
    indirect=["server"],
)
def test_is_secure_repository(server, expected):
    assert APIEndpoint(url=f"{server[0]}:{server[1]}").is_secure_repository() == expected


def test_is_secure_repository_timeout(blocking_https_server):
    with pytest.raises(socket.timeout):
        assert APIEndpoint(url=f"{blocking_https_server[0]}:{blocking_https_server[1]}").is_secure_repository(
            timeout=10.0
        )


@pytest.mark.parametrize(
    ("url", "support_https", "expected"),
    [
        ("127.0.0.1", False, "127.0.0.1:80"),
        ("127.0.0.1", True, "127.0.0.1:443"),
        ("127.0.0.1:5000", False, "127.0.0.1:5000"),
        ("127.0.0.1:5000", True, "127.0.0.1:5000"),
    ],
)
def test_api_base_url(url, support_https, expected):
    with mock.patch(
        "paasng.utils.moby_distribution.spec.endpoint.APIEndpoint.is_secure_repository",
        return_value=[support_https, False],
    ):
        assert APIEndpoint(url=url).api_base_url == expected
