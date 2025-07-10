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

import pytest

from paasng.utils.text import (
    BraceOnlyTemplate,
    basic_str_format,
    calculate_percentage,
    camel_to_snake,
    remove_suffix,
    strip_html_tags,
)


class TestStripHTMLTags:
    @pytest.mark.parametrize(
        ("s", "reserved_tags", "result"),
        [
            ("foo", [], "foo"),
            ("foo<bold></bold>bar", [], "foobar"),
            ("foo<hl>bar</hl>", ["<hl>", "</hl>"], "foo<hl>bar</hl>"),
            ("<blue>foo</blue><hl>bar</hl>", ["<hl>", "</hl>"], "foo<hl>bar</hl>"),
        ],
    )
    def test_normal(self, s, reserved_tags, result):
        assert strip_html_tags(s, reserved_tags=reserved_tags) == result


@pytest.mark.parametrize(
    ("input_", "suffix", "output"),
    [
        ("foo", "bar", "foo"),
        ("foobar", "bar", "foo"),
        ("foobar", "foobar", ""),
    ],
)
def test_remove_suffix(input_, suffix, output):
    assert remove_suffix(input_, suffix) == output


@pytest.mark.parametrize(
    ("input_", "output"),
    [
        ("BkSvnSourceTypeSpec", "bk_svn_source_type_spec"),
        ("bk_svn", "bk_svn"),
    ],
)
def test_camel_to_snake(input_, output):
    assert camel_to_snake(input_) == output


@pytest.mark.parametrize(
    ("x", "y", "decimal_places", "expected"),
    [
        (1, 1, 2, "100.00%"),  # 1 / 1 = 1.00
        (1, 2, 2, "50.00%"),  # 1 / 2 = 0.50
        (1, 3, 2, "33.33%"),  # 1 / 3 = 0.33
        (1, 4, 2, "25.00%"),  # 1 / 4 = 0.25
        (1, 5, 2, "20.00%"),  # 1 / 5 = 0.20
        (5, 2, 2, "250.00%"),  # 5 / 2 == 2.50, result > 1
        (1, 0, 2, None),  # y cannot be 0
        (1, 1, 11, None),  # maximum precision limit exceeded
        (1, 1, 1, "100.0%"),  # decimal_places = 1
        (1, 1, 0, "100%"),  # decimal_places = 0
        (1, 1, -1, None),  # decimal_places = -1
        (0, 1, 2, "<0.01%"),  # x = 0
        (1, 1, 10, "100.0000000000%"),  # decimal_places = 10
        (1, 1, 9, "100.000000000%"),  # decimal_places = 9
        (1, 1, 8, "100.00000000%"),  # decimal_places = 8
        (1, 1, 7, "100.0000000%"),  # decimal_places = 7
        (1, 1, 6, "100.000000%"),  # decimal_places = 6
        (1, 1, 5, "100.00000%"),  # decimal_places = 5
        (1, 1, 4, "100.0000%"),  # decimal_places = 4
        (1, 1, 3, "100.000%"),  # decimal_places = 3
        (1, 10**13, 10, "<0.0000000001%"),  # result = 0.0000000000001, result < min_precision
        (1, 10**12, 9, "<0.000000001%"),  # result = 0.000000000001, result < min_precision
        (1, 10**11, 8, "<0.00000001%"),  # result = 0.00000000001, result < min_precision
        (1, 10**10, 7, "<0.0000001%"),  # result = 0.0000000001, result < min_precision
        (1, 10**9, 6, "<0.000001%"),  # result = 0.000000001, result < min_precision
        (1, 10**8, 5, "<0.00001%"),  # result = 0.00000001, result < min_precision
        (1, 10**7, 4, "<0.0001%"),  # result = 0.0000001, result < min_precision
        (1, 10**6, 3, "<0.001%"),  # result = 0.000001, result < min_precision
        (1, 10**5, 2, "<0.01%"),  # result = 0.00001, result < min_precision
        (1, 10**4, 1, "<0.1%"),  # result = 0.0001, result < min_precision
        (1, 10**3, 0, "<1%"),  # result = 0.001, result < min_precision
    ],
)
def test_calculate_percentage(x, y, decimal_places, expected):
    # 如果期望值为None，则应该抛出异常
    if expected is None:
        with pytest.raises(ValueError, match=r".*"):
            calculate_percentage(x, y, decimal_places)
    else:
        # 否则，应该返回期望值
        assert calculate_percentage(x, y, decimal_places) == expected


class TestBraceOnlyTemplate:
    @pytest.mark.parametrize(
        ("template_str", "kwargs", "expected"),
        [
            # Basic substitution
            ("Hello {name}, welcome to {place}!", {"name": "foo", "place": "bar"}, "Hello foo, welcome to bar!"),
            # Variable inside word
            ("prefix_{var}_suffix", {"var": "test"}, "prefix_test_suffix"),
            # Underscore variable
            ("{underscore_var}", {"underscore_var": "value"}, "value"),
        ],
    )
    def test_various_valid_patterns(self, template_str, kwargs, expected):
        template = BraceOnlyTemplate(template_str)
        assert template.substitute(**kwargs) == expected

    def test_escaped_braces(self):
        # Only "{" needs to be escaped
        template = BraceOnlyTemplate("Use {{ to escape braces, like {{name}")
        assert template.substitute(name="foo") == "Use { to escape braces, like {name}"

    def test_no_substitution_needed(self):
        template = BraceOnlyTemplate("No variables here!")
        assert template.substitute() == "No variables here!"

    def test_missing_variable_raises_error(self):
        template = BraceOnlyTemplate("Hello {name}!")
        with pytest.raises(KeyError):
            template.substitute()


class Test__basic_str_format:
    def test_basic(self):
        assert basic_str_format("Hello {name}!", {"name": "foo"}) == "Hello foo!"

    def test_index_access_should_fail(self):
        with pytest.raises(ValueError, match="Invalid placeholder .*"):
            basic_str_format("Hello {names[0]}!", {"names": "foobar"})
