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

import random
import re
import string
import uuid
from typing import Collection

UNICODE_ASCII_CHARACTER_SET = "abcdefghijklmnopqrstuvwxyz" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "0123456789"


# From oauthlib.common
def generate_token(length=30, chars=UNICODE_ASCII_CHARACTER_SET):
    """Generates a non-guessable OAuth token

    OAuth (1 and 2) does not specify the format of tokens except that they
    should be strings of random characters. Tokens should not be guessable
    and entropy when generating the random characters is important. Which is
    why SystemRandom is used instead of the default random.choice method.
    """
    rand = random.SystemRandom()
    return "".join(rand.choice(chars) for x in range(length))


RE_TAG = re.compile("<.*?>")


def strip_html_tags(s: str, reserved_tags: Collection[str] | None = None) -> str:  # noqa: B006
    """Remove all HTML tags in string except those matching `reserved_tags`.

    :param reserved_tags: Tags were reserved from removing, default to []
    """
    reserved_tags = reserved_tags or []

    performed_tag_pairs = []
    # Replace reserved tags with random uuid string
    for tag in reserved_tags:
        placeholder = uuid.uuid4().hex
        s = s.replace(tag, placeholder)
        performed_tag_pairs.append((tag, placeholder))

    result = re.sub(RE_TAG, "", s)

    # Restore reserved tags
    # NOTE: Current approach's time complexity is O(length_of_string*length_of_reserved_tags), which means it may
    # become slow when there are many reserved tags. Using Trie structure could help improving the performance.
    for tag, placeholder in performed_tag_pairs:
        result = result.replace(placeholder, tag)

    return result


def remove_suffix(s: str, suffix: str) -> str:
    """If given string endswith `suffix`, remove the suffix and return the new string"""
    if s.endswith(suffix):
        return s[: -len(suffix)]
    return s


def remove_prefix(s: str, prefix: str) -> str:
    """If given string startswith `prefix`, remove the prefix and return the new string"""
    if s.startswith(prefix):
        return s[len(prefix) :]
    return s


def camel_to_snake(name: str) -> str:
    """Turn CamelCase string input snake_case.

    >>> camel_to_snake("FooBarBazQux")
    foo_bar_baz_qux
    >>> camel_to_snake("fooBarBazQux")
    foo_bar_baz_qux
    >>> camel_to_snake("AFooBarBazQux")
    a_foo_bar_baz_qux
    >>> camel_to_snake("aFooBarBazQux")
    a_foo_bar_baz_qux
    >>> camel_to_snake("FBI")
    fbi
    """
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def calculate_percentage(x: float, y: float, decimal_places: int = 2) -> str:
    """
    计算 x 除以 y 的值，并将结果转换为百分比的字符串形式。

    如果 y 等于0，则抛出ValueError。
    如果结果小于最小精度（默认为0.01%），则返回 "<最小精度%"。
    否则，返回指定位数小数的百分比。

    :param x: 要除的被除数 (float)
    :param y: 要除的除数 (float)
    :param decimal_places: 要保留的小数位数 (int, optional)，默认值为2
    :return: x 除以 y 的值，转换为百分比的字符串形式 (str)
    """
    if y == 0:
        raise ValueError("y cannot be 0")
    if decimal_places > 10:
        raise ValueError("maximum precision limit exceeded")
    if decimal_places < 0:
        raise ValueError("decimal cannot be negative")
    result = x / y
    # 最小精度
    min_precision = 1 / 100 / 10**decimal_places
    # 如果结果小于最小精度，则返回 "<最小精度%"
    if result < min_precision:
        return "<{:.{decimal_places}%}".format(min_precision, decimal_places=decimal_places)
    # 否则，将结果转换为百分制，并保留指定位数的小数
    else:
        return "{:.{decimal_places}%}".format(result, decimal_places=decimal_places)


class BraceOnlyTemplate(string.Template):
    """A template class similar to `string.Template`, but use `{` as the delimiter and
    only supports single-braces formatted variables: `{<name>}`.

    - Use '{{' to escape a single brace
    - Only '{' need to be escaped, '}' is treated as a normal character
    """

    # Override the delimiter property because `string.Template` uses it
    delimiter = "{"

    delim = delimiter
    # The identifier is copied from `string.Template`
    id = r"(?a:[_a-z][_a-z0-9]*)"

    # "named" and "braced" patterns are modified
    pattern = rf"""
        {delim}(?:
            (?P<escaped>{delim})  |   # Escape sequence of two delimiters
            (?P<named>{id})}}     |   # delimiter and a Python identifier, **modified to ends with a bracket**
            (?P<braced>\b\B)      |   # delimiter and a braced identifier, **modified to never match anything**
            (?P<invalid>)             # Other ill-formed delimiter exprs
        )
        """  # type: ignore


def basic_str_format(template: str, context: dict[str, str]) -> str:
    """This function is similar to `str.format`, but only support basic string substitution,
    features such as attribute access and slicing are not supported.

    It's recommended to use this function when the template is untrusted.

    :param template: The template string.
    :param context: The context dictionary.
    :return: The formatted string.
    """
    return BraceOnlyTemplate(template).substitute(**context)
