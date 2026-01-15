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

import io

import pytest
from bkcrypto import constants as bkcrypto_constants
from bkcrypto.asymmetric.options import SM2AsymmetricOptions
from bkcrypto.contrib.basic.ciphers import get_asymmetric_cipher
from blue_krill.contextlib import nullcontext
from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.utils.serializers import (
    Base64FileField,
    ConfigVarReservedKeyValidator,
    EncryptedCharField,
    EncryptedJSONField,
    IntegerOrCharField,
    SafePathField,
)


class Base64FileFieldSLZ(serializers.Serializer):
    file = Base64FileField()


class TestBase64FileField:
    @pytest.mark.parametrize(
        ("data", "ctx"),
        [
            ("base64,MQ==", nullcontext(b"1")),
            (b"1", nullcontext(b"1")),
            ("MQ==", pytest.raises(ValidationError, match='"MQ==" is not a valid format, please startswith "base64')),
            ("base64,MQ", pytest.raises(ValidationError, match='"MQ" is not a valid base64, please check it.')),
        ],
    )
    def test_to_internal_value(self, data, ctx):
        slz = Base64FileFieldSLZ(data={"file": data})
        with ctx as expected:
            slz.is_valid(raise_exception=True)
            assert slz.validated_data["file"].read() == expected

    @pytest.mark.parametrize(
        ("data", "ctx"),
        [
            ("base64,MQ==", nullcontext("base64,MQ==")),
            (b"1", nullcontext("base64,MQ==")),
            ("1", nullcontext("base64,MQ==")),
            (io.StringIO("1"), nullcontext("base64,MQ==")),
            (io.BytesIO(b"1"), nullcontext("base64,MQ==")),
            ([], pytest.raises(ValueError, match=r"Unsupported value: \[\]")),
        ],
    )
    def test_to_representation(self, data, ctx):
        slz = Base64FileFieldSLZ({"file": data})
        with ctx as expected:
            assert slz.data == {"file": expected}


@pytest.mark.parametrize(
    ("protected_key_list", "protected_prefix_list", "key", "expected"),
    [
        ([], [], "foo", nullcontext()),
        (["foo"], [], "foo", pytest.raises(ValidationError)),
        (["foo_"], [], "foo", nullcontext()),
        (["f00"], [], "foo", nullcontext()),
        ([], ["f"], "foo", pytest.raises(ValidationError)),
        ([], ["foo"], "foo", pytest.raises(ValidationError)),
        ([], ["foo_"], "foo", nullcontext()),
    ],
)
def test_config_var_reserved_key_validator(protected_key_list, protected_prefix_list, key, expected):
    v = ConfigVarReservedKeyValidator(protected_key_list, protected_prefix_list)
    with expected:
        v(key)


class IntegerOrCharFieldSLZ(serializers.Serializer):
    port = IntegerOrCharField()


class TestIntegerOrCharField:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            ("http", "http"),
            ("${PORT}", "${PORT}"),
            ("8080", 8080),
            (8080, 8080),
        ],
    )
    def test_to_internal_value(self, data, expected):
        slz = IntegerOrCharFieldSLZ(data={"port": data})
        slz.is_valid(raise_exception=True)
        assert slz.validated_data["port"] == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            ("http", "http"),
            ("${PORT}", "${PORT}"),
            ("8080", 8080),
            (8080, 8080),
        ],
    )
    def test_to_representation(self, data, expected):
        slz = IntegerOrCharFieldSLZ({"port": data})
        assert slz.data == {"port": expected}


class SafePathSLZ(serializers.Serializer):
    safe_path = SafePathField(allow_blank=True)


class TestSafePathField:
    @pytest.mark.parametrize(
        "safe_path",
        [
            "",
            "foo",
            "foo/",
            "foo/bar",
            "foo/bar/baz",
            "./foo/bar/baz",
        ],
    )
    def test_valid(self, safe_path):
        slz = SafePathSLZ(data={"safe_path": safe_path})
        assert slz.is_valid() is True

    @pytest.mark.parametrize(
        "safe_path",
        [
            "..",
            "/etc/passwd",
            "../foo/bar/baz",
            "foo/../bar/baz",
            "foo/../../bar/baz",
            "foo/%2e%2e/bar/baz",
            "foo/%2e%2e%2fbar/baz",
            "/safe////../etc/passwd",
        ],
    )
    def test_invalid(self, safe_path):
        slz = SafePathSLZ(data={"safe_path": safe_path})
        assert slz.is_valid() is False


# SM2 测试密钥对
SM2_PUBLIC_KEY = "-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoEcz1UBgi0DQgAEU87uYBCj19QKO0cm6kjsBWhEIOeT\ndlRDjt0OXvh+JUnr7ZoWTyXAi/SidN3g4nlz337+iw8T6LC2yGWuUnlQYg==\n-----END PUBLIC KEY-----\n"
SM2_PRIVATE_KEY = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIOzo3tQc6DUzdt1+rV/SqNxj9OgPxdcnWyXuDUMaR59moAoGCCqBHM9V\nAYItoUQDQgAEU87uYBCj19QKO0cm6kjsBWhEIOeTdlRDjt0OXvh+JUnr7ZoWTyXA\ni/SidN3g4nlz337+iw8T6LC2yGWuUnlQYg==\n-----END EC PRIVATE KEY-----\n"


@pytest.fixture(scope="session")
def enable_frontend_encrypt():
    """配置前端加密功能"""
    settings.ENABLE_FRONTEND_ENCRYPT = True
    settings.FRONTEND_ENCRYPT_PUBLIC_KEY = SM2_PUBLIC_KEY
    settings.FRONTEND_ENCRYPT_PRIVATE_KEY = SM2_PRIVATE_KEY


def encrypted_value(value: str) -> str:
    """使用测试密钥加密值"""
    cipher = get_asymmetric_cipher(
        cipher_type=bkcrypto_constants.AsymmetricCipherType.SM2.value,
        cipher_options={
            bkcrypto_constants.AsymmetricCipherType.SM2.value: SM2AsymmetricOptions(
                public_key_string=SM2_PUBLIC_KEY,
                private_key_string=SM2_PRIVATE_KEY,
            ),
        },
    )
    return cipher.encrypt(value)


class EncryptedCharFieldSLZ(serializers.Serializer):
    username = EncryptedCharField(required=False)
    password = EncryptedCharField()


@pytest.mark.usefixtures("enable_frontend_encrypt")
class TestEncryptedCharField:
    @pytest.mark.parametrize(
        ("plain_value", "encrypted_value", "ctx"),
        [
            ("test_value", encrypted_value("test_value"), nullcontext("test_value")),
            ("#/@!>?><09123...。", encrypted_value("#/@!>?><09123...。"), nullcontext()),
            ("", encrypted_value(""), pytest.raises(ValidationError)),
            ("test_value", "invalid_encrypted_value", pytest.raises(ValidationError)),
        ],
        ids=["valid_test_value", "valid_special_chars", "empty_string", "invalid_encrypted"],
    )
    def test_decrypt(self, plain_value, encrypted_value, ctx):
        with ctx:
            slz = EncryptedCharFieldSLZ(data={"password": encrypted_value})
            slz.is_valid(raise_exception=True)
            assert slz.validated_data["password"] == plain_value


class EncryptedJSONFieldSLZ(serializers.Serializer):
    # 指定 EncryptedJSONFieldSLZ(自身) 和 NestedSLZ2 启用加密
    encrypted_json = EncryptedJSONField(
        encrypted_fields=["password", "user.password"],
        encrypt_enabled_slz=["EncryptedJSONFieldSLZ", "NestedSLZ2"],
    )


class NestedSLZ(serializers.Serializer):
    data = EncryptedJSONFieldSLZ()


class NestedSLZ2(serializers.Serializer):
    data = EncryptedJSONFieldSLZ()


@pytest.mark.usefixtures("enable_frontend_encrypt")
class TestEncryptedJSONField:
    @pytest.mark.parametrize(
        ("slz_input", "slz_output", "ctx"),
        [
            (
                {"foo": "bar", "password": encrypted_value("test_value")},
                {"foo": "bar", "password": "test_value"},
                nullcontext(),
            ),
            (
                {"foo": "bar", "password": "invalid_encrypted_value"},
                None,
                pytest.raises(ValidationError),
            ),
            (
                {"foo": "bar", "user": {"username": "test", "password": encrypted_value("test_value")}},
                {"foo": "bar", "user": {"username": "test", "password": "test_value"}},
                nullcontext(),
            ),
            (
                {"foo": "bar", "user": {"username": "test", "password": "invalid_encrypted_value"}},
                None,
                pytest.raises(ValidationError),
            ),
        ],
        ids=["valid_password", "invalid_password", "valid_user_password", "invalid_user_password"],
    )
    def test_decrypt(self, slz_input, slz_output, ctx):
        slz = EncryptedJSONFieldSLZ(data={"encrypted_json": slz_input})
        with ctx:
            assert slz.is_valid(raise_exception=True)
            assert slz.data["encrypted_json"] == slz_output

    @pytest.mark.parametrize(
        ("slz_cls", "input", "ctx"),
        [
            (
                NestedSLZ,
                {"data": {"encrypted_json": {"username": "test", "password": "test-value"}}},
                nullcontext("test-value"),
            ),
            (
                NestedSLZ2,
                {"data": {"encrypted_json": {"username": "test", "password": "test-value"}}},
                pytest.raises(ValidationError),
            ),
            (
                NestedSLZ2,
                {"data": {"encrypted_json": {"username": "test", "password": encrypted_value("test-value")}}},
                nullcontext("test-value"),
            ),
        ],
    )
    def test_skip_encrypt(self, slz_cls: serializers.Serializer, input, ctx):
        slz = slz_cls(data=input)
        with ctx as expected:
            slz.is_valid(raise_exception=True)
            assert slz.validated_data["data"]["encrypted_json"]["password"] == expected

    @pytest.mark.parametrize(
        ("input", "ctx"),
        [
            (
                {"encrypted_json": {"username": "test", "password": "test-value"}},
                pytest.raises(ValidationError),
            ),
            (
                {"encrypted_json": {"username": "test", "password": encrypted_value("test-value")}},
                nullcontext("test-value"),
            ),
        ],
    )
    def test_skip_encrypt2(self, input, ctx):
        slz = EncryptedJSONFieldSLZ(data=input)
        with ctx as expected:
            slz.is_valid(raise_exception=True)
            assert slz.validated_data["encrypted_json"]["password"] == expected

    def test_no_parent_error(self):
        field = EncryptedJSONField(encrypt_enabled_slz=["A"])
        with pytest.raises(AssertionError):
            field.to_internal_value({"username": "test", "password": "test-value"})
