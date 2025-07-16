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
from blue_krill.contextlib import nullcontext
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.utils.serializers import Base64FileField, ConfigVarReservedKeyValidator, IntegerOrCharField, SafePathField


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
