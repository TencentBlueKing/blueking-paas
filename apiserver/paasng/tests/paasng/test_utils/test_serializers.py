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


class EncryptedCharFieldSLZ(serializers.Serializer):
    username = EncryptedCharField(required=False)
    password = EncryptedCharField(must_encrypt=True)


class TestEncryptedCharField:
    @pytest.fixture
    def encrypted_value(self):
        """使用默认的公钥加密一个测试值"""

        cipher = get_asymmetric_cipher(
            cipher_type=bkcrypto_constants.AsymmetricCipherType.SM2.value,
            cipher_options={
                bkcrypto_constants.AsymmetricCipherType.SM2.value: SM2AsymmetricOptions(
                    public_key_string=settings.FRONTEND_ENCRYPT_SM2_PUBLIC_KEY,
                    private_key_string=settings.FRONTEND_ENCRYPT_SM2_PRIVATE_KEY,
                ),
            },
        )

        return cipher.encrypt("test_value")

    def test_decrypt(self, encrypted_value):
        slz = EncryptedCharFieldSLZ(data={settings.FRONTEND_ENCRYPT_FIELD_PREFIX + "password": encrypted_value})
        slz.is_valid(raise_exception=True)
        assert slz.validated_data["password"] == "test_value"

    @pytest.mark.parametrize(
        ("data", "ctx"),
        [
            ({"username": "test_value"}, pytest.raises(ValidationError, match="required")),
            ({"password": "test_value"}, pytest.raises(ValidationError, match="required")),
            ({"_encrypted_password": "test_value"}, pytest.raises(ValidationError, match="base64 decode failed")),
        ],
    )
    def test_must_encrypt(self, data, ctx):
        slz = EncryptedCharFieldSLZ(data=data)
        with ctx:
            slz.is_valid(raise_exception=True)


class EncryptedJSONFieldSLZ(serializers.Serializer):
    encrypted_json = EncryptedJSONField(max_decrypt_node_num=10, max_loop_num=50)


class TestEncryptedJSONField:
    @pytest.fixture
    def encrypted_value(self):
        """使用默认的公钥加密一个测试值"""
        cipher = get_asymmetric_cipher(
            cipher_type=bkcrypto_constants.AsymmetricCipherType.SM2.value,
            cipher_options={
                bkcrypto_constants.AsymmetricCipherType.SM2.value: SM2AsymmetricOptions(
                    public_key_string=settings.FRONTEND_ENCRYPT_SM2_PUBLIC_KEY,
                    private_key_string=settings.FRONTEND_ENCRYPT_SM2_PRIVATE_KEY,
                ),
            },
        )
        return cipher.encrypt("test-value")

    def test_decrypt(self, encrypted_value):
        slz = EncryptedJSONFieldSLZ(
            data={
                "encrypted_json": {"foo": "bar", f"{settings.FRONTEND_ENCRYPT_FIELD_PREFIX}password": encrypted_value}
            }
        )
        assert slz.is_valid()
        assert slz.validated_data["encrypted_json"]["password"] == "test-value"

    @pytest.mark.parametrize(
        ("encrypted_count", "dict_count", "ctx"),
        [
            # 加密节点数量边界
            (10, None, nullcontext()),
            (11, None, pytest.raises(ValidationError)),
            # 总节点数量边界（不加密）
            (None, 50, nullcontext()),
            (None, 52, pytest.raises(ValidationError)),
        ],
    )
    def test_big_data_decrypt(self, encrypted_value, encrypted_count, dict_count, ctx):
        if encrypted_count is not None:
            data = {
                "encrypted_json": {
                    f"{settings.FRONTEND_ENCRYPT_FIELD_PREFIX}{idx}": encrypted_value for idx in range(encrypted_count)
                }
            }
        else:
            data = {"encrypted_json": {f"foo_{idx}": {} for idx in range(dict_count)}}

        slz = EncryptedJSONFieldSLZ(data=data)
        with ctx:
            slz.is_valid(raise_exception=True)
