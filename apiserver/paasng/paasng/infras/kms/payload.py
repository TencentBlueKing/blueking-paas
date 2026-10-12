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

"""冻结敏感变量的明文格式

明文只在本进程内存中存在，用于交给 KMS 信封加密，不落库、不写日志。格式为：
{"schema_version": 1, "config_version_id": "...", "module_environment_id": "...", "env": {...}}
"""

import json
from collections.abc import Mapping

from .constants import FROZEN_PAYLOAD_SCHEMA_VERSION, PLAINTEXT_MAX_CHARS
from .exceptions import KMSValidationError


def build_frozen_payload(*, config_version_id: str, module_environment_id: str, env_vars: Mapping[str, str]) -> str:
    """生成稳定序列化的明文 JSON。超出 KMS 明文上限时直接报错，不自动拆分；错误信息不包含变量内容"""
    for key, value in env_vars.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise KMSValidationError("sensitive env vars must be string key/value pairs")

    payload = {
        "schema_version": FROZEN_PAYLOAD_SCHEMA_VERSION,
        "config_version_id": config_version_id,
        "module_environment_id": module_environment_id,
        "env": dict(env_vars),
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(text) > PLAINTEXT_MAX_CHARS:
        raise KMSValidationError(f"sensitive payload exceeds {PLAINTEXT_MAX_CHARS} characters, split is not supported")
    return text
