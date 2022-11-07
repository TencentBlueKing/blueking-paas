# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import random
import re
import uuid
from typing import Collection

UNICODE_ASCII_CHARACTER_SET = 'abcdefghijklmnopqrstuvwxyz' 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' '0123456789'


# From oauthlib.common
def generate_token(length=30, chars=UNICODE_ASCII_CHARACTER_SET):
    """Generates a non-guessable OAuth token

    OAuth (1 and 2) does not specify the format of tokens except that they
    should be strings of random characters. Tokens should not be guessable
    and entropy when generating the random characters is important. Which is
    why SystemRandom is used instead of the default random.choice method.
    """
    rand = random.SystemRandom()
    return ''.join(rand.choice(chars) for x in range(length))


RE_TAG = re.compile('<.*?>')


def strip_html_tags(s: str, reserved_tags: Collection[str] = []) -> str:
    """Remove all HTML tags in string except those matching `reserved_tags`.

    :param reserved_tags: Tags were reserved from removing, default to []
    """
    performed_tag_pairs = []
    # Replace reserved tags with random uuid string
    for tag in reserved_tags:
        placeholder = uuid.uuid4().hex
        s = s.replace(tag, placeholder)
        performed_tag_pairs.append((tag, placeholder))

    result = re.sub(RE_TAG, '', s)

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
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
