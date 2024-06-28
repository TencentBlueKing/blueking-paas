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
from urllib.parse import parse_qs, quote

from requests import Request

import paasng.utils.masked_curlify as curlify
from paasng.utils.masked_curlify import MASKED_CONTENT


class TestToCurlMasked:
    def test_mask_query_params(self):
        test_request = Request("GET", "https://example.com/api?BK_PASSWORD=123456&api_key=abcdef")
        prepared_request = test_request.prepare()

        curlify.to_curl(prepared_request)

        assert f"BK_PASSWORD={quote(MASKED_CONTENT)}" in str(prepared_request.url)
        assert f"api_key={quote(MASKED_CONTENT)}" in str(prepared_request.url)

    def test_mask_json_data(self):
        test_request = Request("POST", "https://example.com/api", json={"BK_PASSWORD": "123456", "api_key": "abcdef"})
        prepared_request = test_request.prepare()

        curlify.to_curl(prepared_request)

        json_data = json.loads(prepared_request.body)  # type: ignore
        assert json_data["BK_PASSWORD"] == MASKED_CONTENT
        assert json_data["api_key"] == MASKED_CONTENT

    def test_mask_form_data(self):
        test_request = Request("POST", "https://example.com/api", data={"BK_PASSWORD": "123456", "api_key": "abcdef"})
        prepared_request = test_request.prepare()

        curlify.to_curl(prepared_request)

        form_data = parse_qs(prepared_request.body)  # type: ignore
        assert form_data["BK_PASSWORD"] == [MASKED_CONTENT]
        assert form_data["api_key"] == [MASKED_CONTENT]

    def test_mask_header_data(self):
        test_request = Request(
            "POST", "https://example.com/api", headers={"BK_PASSWORD": "123456", "api_key": "abcdef"}
        )
        prepared_request = test_request.prepare()

        curlify.to_curl(prepared_request)

        assert prepared_request.headers["BK_PASSWORD"] == MASKED_CONTENT
        assert prepared_request.headers["api_key"] == MASKED_CONTENT
