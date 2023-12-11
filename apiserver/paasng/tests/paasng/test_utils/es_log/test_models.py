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
import datetime

import cattr
import pytest
import pytz
from attrs import converters, define

from paasng.utils.es_log.misc import count_filters_options, flatten_structure, format_timestamp
from paasng.utils.es_log.models import FieldFilter, LogLine, extra_field


@pytest.mark.parametrize(
    ("value", "input_format", "expected"),
    [
        (1000, "timestamp[s]", 1000),
        (1000, "timestamp[ns]", 1),
        (datetime.datetime(1970, 1, 1), "datetime", 0),
        (datetime.datetime(1970, 1, 1).replace(tzinfo=pytz.timezone("UTC")), "datetime", 0),
        (datetime.datetime(1970, 1, 1).replace(tzinfo=pytz.timezone("Asia/Shanghai")), "datetime", -29160),
    ],
)
def test_format_timestamp(value, input_format, expected):
    assert format_timestamp(value, input_format) == expected


@pytest.mark.parametrize(
    ("logs", "filters", "expected"),
    [
        # 测试忽略所有日志中不存在的字段
        (
            [
                {"log": "xxx"},
                {"log": "yyy"},
                {"log": "xxx"},
                {"log": "yyy"},
            ],
            {"log": FieldFilter(name="log", key="log.keyword"), "noise": FieldFilter(name="noise", key="noise")},
            [FieldFilter(name="log", key="log.keyword", options=[("xxx", "50.00%"), ("yyy", "50.00%")], total=4)],
        ),
        # 测试层级嵌套的日志和忽略未声明的字段
        (
            [
                {"nested": {"log": "x"}},
                {"nested": {"log": "y"}},
                {"nested": {"log": "y"}},
                {"nested": {"log": "x"}},
                {"nested": {"...": "..."}},
            ],
            {"nested.log": FieldFilter(name="nested.log", key="nested.log")},
            [FieldFilter(name="nested.log", key="nested.log", options=[("x", "50.00%"), ("y", "50.00%")], total=4)],
        ),
    ],
)
def test_count_filters_options(logs, filters, expected):
    assert count_filters_options(logs, filters) == expected


@pytest.mark.parametrize(
    ("structured_fields", "parent", "expected_output"),
    [
        # 结构体为空，父级字段为空（即默认值）
        ({}, None, {}),
        # 结构体只包含一个字段，父级字段为空（即默认值）
        ({"foo": "bar"}, None, {"foo": "bar"}),
        # 结构体包含嵌套结构体，父级字段为空（即默认值）
        ({"foo": {"bar": "baz"}}, None, {"foo.bar": "baz"}),
        # 结构体包含嵌套结构体，父级字段不为空。
        ({"foo": {"bar": "baz"}}, "parent", {"parent.foo.bar": "baz"}),
        # 结构体为空，父级字段不为空
        ({}, "parent", {}),
        # 结构体包含嵌套结构体和普通字段，父级字段为空
        ({"foo": {"bar": "baz"}, "qux": "quux"}, None, {"foo.bar": "baz", "qux": "quux"}),
        # 结构体包含嵌套结构体和普通字段，父级字段不为空
        ({"foo": {"bar": "baz"}, "qux": "quux"}, "parent", {"parent.foo.bar": "baz", "parent.qux": "quux"}),
        # 结构体包含多层嵌套结构体，父级字段为空
        ({"foo": {"bar": {"baz": "qux"}}}, None, {"foo.bar.baz": "qux"}),
        # 结构体包含多层嵌套结构体，父级字段不为空
        ({"foo": {"bar": {"baz": "qux"}}}, "parent", {"parent.foo.bar.baz": "qux"}),
        # 结构体包含多层嵌套结构体，嵌套结构体中包含普通字段
        (
            {"foo": {"bar": {"baz": "qux", "quux": "corge"}}},
            "parent",
            {"parent.foo.bar.baz": "qux", "parent.foo.bar.quux": "corge"},
        ),
    ],
)
def test_flatten_structure(structured_fields, parent, expected_output):
    assert flatten_structure(structured_fields, parent) == expected_output


def _build_extra_data(data):
    return {"message": "", "timestamp": 0, "raw": data}


def _build_expected(data):
    return {"message": "", "timestamp": 0, **data}


@pytest.mark.parametrize(
    ("extra_fields", "data", "expected"),
    [
        (
            {
                "plugin_code": extra_field("app_code"),
            },
            _build_extra_data({"app_code": "foo"}),
            _build_expected({"plugin_code": "foo"}),
        ),
        (
            {
                "plugin_code": extra_field("app_code", converter=converters.optional(str)),
            },
            _build_extra_data({"app_code": 1}),
            _build_expected({"plugin_code": "1"}),
        ),
        (
            {
                "plugin_code": extra_field("app_code", converter=converters.optional(str)),
            },
            _build_extra_data({"app_code": None}),
            _build_expected({"plugin_code": None}),
        ),
        (
            {
                "plugin_code": extra_field(lambda raw: raw["???????????"], converter=converters.optional(str)),
            },
            _build_extra_data({"???????????": 0}),
            _build_expected({"plugin_code": "0"}),
        ),
    ],
)
def test_extra_field(extra_fields, data, expected):
    model_class = define(type("dummy", (LogLine,), extra_fields))
    log = cattr.structure(data, model_class)  # type: ignore
    assert cattr.unstructure(log) == {**expected, "raw": data["raw"]}
