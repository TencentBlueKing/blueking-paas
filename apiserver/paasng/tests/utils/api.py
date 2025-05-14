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

import json

from requests import Response
from rest_framework.utils.encoders import JSONEncoder


def mock_json_response(data, status_code=200):
    """Generates a mocked response, usually used for requests library patch"""
    resp = Response()
    resp.url = "https://example.com"
    resp.encoding = "utf-8"
    resp._content = json.dumps(data, cls=JSONEncoder).encode("utf-8")
    resp.status_code = status_code
    return resp
