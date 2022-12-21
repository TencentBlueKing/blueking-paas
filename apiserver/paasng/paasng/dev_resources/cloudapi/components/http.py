# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
"""
http基础方法

Rules:
1. POST/DELETE/PUT: json in
2. GET带参数，HEAD不带参数
3. 所有请求 json out，如果resp.json报错, 则是接口问题
"""
import logging
from typing import Tuple, Union

import curlify
import requests

logger = logging.getLogger(__name__)


def _http_request(method: str, url: str, **kwargs) -> Tuple[bool, Union[None, dict, list]]:
    try:
        resp = requests.request(method, url, **kwargs)
    except requests.exceptions.RequestException:
        logger.exception("http request error! method: %s, url: %s, kwargs: %s", method, url, kwargs)
        return False, None

    logger.debug("request third-party api: %s", curlify.to_curl(resp.request))

    try:
        return True, resp.json()
    except Exception:
        logger.exception(
            "response json error! method: %s, url: %s, kwargs: %s, response.status_code: %s, response.text: %s",
            method,
            url,
            kwargs,
            resp.status_code,
            resp.text,
        )
        return False, None


def http_get(url: str, **kwargs) -> Tuple[bool, Union[None, dict, list]]:
    return _http_request(method="GET", url=url, **kwargs)


def http_post(url: str, **kwargs) -> Tuple[bool, Union[None, dict, list]]:
    return _http_request(method="POST", url=url, **kwargs)


def http_put(url: str, **kwargs) -> Tuple[bool, Union[None, dict, list]]:
    return _http_request(method="PUT", url=url, **kwargs)


def http_delete(url: str, **kwargs) -> Tuple[bool, Union[None, dict, list]]:
    return _http_request(method="DELETE", url=url, **kwargs)
