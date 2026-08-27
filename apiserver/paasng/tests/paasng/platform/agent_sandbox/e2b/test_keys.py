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

import re

import pytest

from paasng.platform.agent_sandbox.e2b.constants import API_KEY_RANDOM_BYTES
from paasng.platform.agent_sandbox.e2b.keys import generate_api_key, is_well_formed, make_display_prefix

# e2b SDK 客户端侧的校验正则，key 不满足它时 SDK 在本地就会拒绝，请求根本发不出去。
# 与 e2b/api/__init__.py 的 _API_KEY_PATTERN 保持一致
SDK_API_KEY_PATTERN = re.compile(r"\Ae2b_[0-9a-f]+\Z")


def test_generated_key_passes_sdk_validation():
    """签发的 key 必须能过 SDK 的客户端校验，否则请求在本地就发不出去。"""
    assert SDK_API_KEY_PATTERN.match(generate_api_key())


def test_key_entropy_meets_security_floor():
    """熵值下限是安全要求，调小 API_KEY_RANDOM_BYTES 时应当在这里被拦下。"""
    assert API_KEY_RANDOM_BYTES * 8 >= 128


def test_display_prefix_is_a_strict_prefix():
    """展示前缀要能用于列表匹配，同时不能等于整个 key。"""
    key = generate_api_key()
    prefix = make_display_prefix(key)

    assert key.startswith(prefix)
    assert len(prefix) < len(key)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("e2b_" + "a" * 40, True),
        # SDK 只要求前缀加十六进制，不限长度
        ("e2b_abc", True),
        ("e2b_", False),
        ("e2b_" + "A" * 40, False),
        ("e2b_" + "g" * 40, False),
        ("sk_" + "a" * 40, False),
        ("", False),
        ("e2b_abc\n", False),
    ],
)
def test_is_well_formed(key, expected):
    assert is_well_formed(key) is expected
