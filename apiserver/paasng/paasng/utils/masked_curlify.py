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

import json
from typing import Any, Dict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import curlify
import requests

# 脱敏需要处理的字段
# 包含这些内容的字段都会被脱敏，例如 X-BK-APP-SECRET 也会被脱敏处理
DEFAULT_SCRUBBED_FIELDS = (
    "password",
    "secret",
    "passwd",
    "api_key",
    "apikey",
    "bk_token",
    "bk_ticket",
    "access_token",
    "auth",
    "credentials",
)

# 敏感信息替换后的内容
MASKED_CONTENT = "******"


def scrub_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Scrub the data, mask all sensitive data fields.

    :return: A new dict, with sensitive data masked as "******".
    """
    if not (isinstance(data, (dict, requests.structures.CaseInsensitiveDict))):
        return data

    def _key_is_sensitive(key: str) -> bool:
        """Check if given key is sensitive."""
        return any(field in key.lower() for field in DEFAULT_SCRUBBED_FIELDS)

    result: Dict[str, Any] = {}

    # Use a stack to avoid recursion
    stack = [(data, result)]
    while stack:
        current_data, current_result = stack.pop()

        for key, value in current_data.items():
            if _key_is_sensitive(key):
                current_result[key] = MASKED_CONTENT
                continue

            # Process nested data by push it to the stack
            if isinstance(value, dict):
                new_dict: Dict[str, Any] = {}
                current_result[key] = new_dict
                stack.append((value, new_dict))
            else:
                current_result[key] = value
    return result


def mask_sensitive_data(request):
    """
    脱敏请求对象中的敏感数据。
    """
    # 脱敏请求头的数据
    request.headers = scrub_data(request.headers)

    # 脱敏 URL 中的查询参数
    url_parts = urlparse(request.url)
    masked_query_params = scrub_data(parse_qs(url_parts.query))

    masked_query = urlencode(masked_query_params, doseq=True)
    masked_url_parts = url_parts._replace(query=masked_query)
    request.url = urlunparse(masked_url_parts)

    # 脱敏 JSON 数据
    if request.headers.get("Content-Type") == "application/json" and request.body:
        try:
            masked_json_data = scrub_data(json.loads(request.body))
            request.body = json.dumps(masked_json_data)
        except json.JSONDecodeError:
            pass

    # 脱敏表单数据
    elif request.headers.get("Content-Type") == "application/x-www-form-urlencoded" and request.body:
        masked_form_data = scrub_data(parse_qs(request.body))
        request.body = urlencode(masked_form_data, doseq=True)

    return request


def to_curl(request, compressed=False, verify=True):
    """将请求对象转换为一个 cURL 命令，同时对敏感信息进行脱敏处理。"""
    masked_request = mask_sensitive_data(request)
    return curlify.to_curl(masked_request, compressed=False, verify=True)
