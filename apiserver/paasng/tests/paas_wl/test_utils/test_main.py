# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from enum import Enum

import pytest
from attrs import define
from django.utils.crypto import get_random_string

from paas_wl.utils.basic import convert_key_to_camel, digest_if_length_exceeded
from paas_wl.utils.constants import make_enum_choices
from paas_wl.utils.models import make_json_field


class TestConstants:
    def test_make_enum_choices(self):
        class FooEnum(Enum):
            RED = 1
            BLUE = 2

        assert make_enum_choices(FooEnum) == [(1, 'RED'), (2, 'BLUE')]


class TestDigestIfLengthExceeded:
    def test_short_str(self):
        assert digest_if_length_exceeded("aaaa", 10) == "aaaa"
        assert digest_if_length_exceeded("aaaa", 4) == "aaaa"

    def test_long_str(self):
        assert len(digest_if_length_exceeded("aaaaaa", 5)) == 5
        assert len(digest_if_length_exceeded("123456789012345678901234567890123456789012345", 41)) == 40
        assert len(digest_if_length_exceeded("123456789012345678901234567890123456789012345", 40)) == 40


@define
class FooType:
    foo: str
    bar: bool = False


def foo_upper_asdict(obj: FooType):
    return {"FOO": obj.foo, "BAR": obj.bar}


class FooCustomAsDict:
    def __init__(self, foo: str, bar: bool = False, baz: float = 1.1):
        self.foo = foo
        self.bar = bar
        self.baz = baz

    def as_dict(self):
        return {
            "bar": self.bar,
            "baz": self.baz,
            "foo": self.foo,
        }


FooTypeField = make_json_field("FooTypeField", FooType)
FooTypeUpperField = make_json_field("FooTypeUpperField", FooType, foo_upper_asdict)
FooCustomAsDictField = make_json_field("FooCustomAsDictField", FooCustomAsDict, FooCustomAsDict.as_dict)


class TestDynamicJSONField:
    def test_make_json_field(self):
        cls_name = get_random_string(32)
        field = make_json_field(cls_name, FooType)
        assert field.__module__ == __name__

    @pytest.mark.parametrize(
        "value, expected, field",
        [
            (FooType(foo="a"), '{"foo": "a", "bar": false}', FooTypeField()),
            (FooType(foo="a", bar=True), '{"foo": "a", "bar": true}', FooTypeField()),
            (FooType(foo="a"), '{"FOO": "a", "BAR": false}', FooTypeUpperField()),
            (FooType(foo="a", bar=True), '{"FOO": "a", "BAR": true}', FooTypeUpperField()),
            (dict(foo="a"), '{"foo": "a"}', FooTypeField()),
            (FooCustomAsDict(foo="a"), '{"bar": false, "baz": 1.1, "foo": "a"}', FooCustomAsDictField()),
            (FooCustomAsDict(foo="a", bar=True), '{"bar": true, "baz": 1.1, "foo": "a"}', FooCustomAsDictField()),
            (
                FooCustomAsDict(foo="a", bar=True, baz=float("inf")),
                '{"bar": true, "baz": Infinity, "foo": "a"}',
                FooCustomAsDictField(),
            ),
        ],
    )
    def test_get_prep_value(self, value, expected, field):
        assert field.get_prep_value(value) == expected


class TestConvertKeyToCamel:
    @pytest.mark.parametrize(
        'data, expected',
        [
            ({}, {}),
            ({'foo_bar': 1, 'baz_qux': 2}, {'fooBar': 1, 'bazQux': 2}),
            ({'foo_bar': {'baz_qux': 1}}, {'fooBar': {'bazQux': 1}}),
            ({'foo_bar': 'foo_bar', 'baz_qux': 'baz_qux'}, {'fooBar': 'foo_bar', 'bazQux': 'baz_qux'}),
        ],
    )
    def test_convert_key_to_camel(self, data, expected):
        assert convert_key_to_camel(data) == expected
