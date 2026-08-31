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

"""e2b API Key 的生成、摘要与格式校验。"""

import hashlib
import re
import secrets

from .constants import API_KEY_DISPLAY_PREFIX_LEN, API_KEY_PREFIX, API_KEY_RANDOM_BYTES

# 与 e2b SDK 的 ``_API_KEY_PATTERN`` 保持一致：前缀加任意长度的小写十六进制。
# 平台签发的 key 长度是固定的，但这里不收紧，以免把 SDK 认为合法的 key 挡在查库之前
API_KEY_PATTERN = re.compile(rf"\A{re.escape(API_KEY_PREFIX)}[0-9a-f]+\Z")


def generate_api_key() -> str:
    """签发一个新的明文 key，熵值为 ``API_KEY_RANDOM_BYTES * 8`` 位。"""
    return API_KEY_PREFIX + secrets.token_hex(API_KEY_RANDOM_BYTES)


def hash_api_key(key: str) -> str:
    """计算 api_key 哈希值"""
    return hashlib.sha256(key.encode()).hexdigest()


def make_display_prefix(key: str) -> str:
    """取明文 key 的前若干位用于列表展示。"""
    return key[:API_KEY_DISPLAY_PREFIX_LEN]


def is_valid_e2b_api_key(key: str) -> bool:
    """是否满足 e2b SDK 的格式约束。

    这里的判断与 SDK 客户端侧的校验保持一致，用于在查库之前挡掉明显非法的 key。
    """
    return bool(API_KEY_PATTERN.match(key))
