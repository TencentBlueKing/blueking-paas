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

import io
import re
from typing import Dict

from attrs import define, field
from requests import Response
from requests.adapters import BaseAdapter


@define
class MockResponse:
    status_code: int = 200
    headers: dict = field(factory=dict)
    body: bytes = b""


class MockAdapter(BaseAdapter):
    def __init__(self):
        super().__init__()
        self.responses: Dict[str, MockResponse] = {}

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        resp = Response()
        resp.request = request

        mock_response = self._find_response(request.url)
        if not mock_response:
            resp.status_code = 404
            return resp

        resp.status_code = mock_response.status_code
        resp.headers = mock_response.headers.copy()
        resp.raw = io.BytesIO(mock_response.body)
        return resp

    def close(self):
        """Nothing bo close, just implement BaseAdapter interface"""

    def register(self, url, response: MockResponse):
        self.responses[url] = response

    def _find_response(self, url):
        if url in self.responses:
            return self.responses[url]

        for pattern, mock_response in self.responses.items():
            if re.fullmatch(pattern, url):
                return mock_response
        return None
