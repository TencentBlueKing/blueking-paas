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
import pytest
from blue_krill.web.std_error import APIError

from paasng.accessories.cloudapi.components.component import BaseComponent


class TestBaseComponent:
    @pytest.mark.parametrize(
        ("mocked_http_ok", "mocked_resp", "will_error"),
        [
            (
                True,
                {"code": 0},
                False,
            ),
            (
                False,
                {"code": 0},
                True,
            ),
            (
                True,
                {},
                True,
            ),
            (
                True,
                {"code": 1, "message": "error"},
                True,
            ),
        ],
    )
    def test_call_api(self, mocker, mocked_http_ok, mocked_resp, will_error):
        def http_func(url, **kwargs):
            return (mocked_http_ok, mocked_resp)

        comp = BaseComponent()

        if will_error:
            with pytest.raises(APIError):
                comp._call_api(http_func, "/api")

            return

        result = comp._call_api(http_func, "/api")
        assert result == mocked_resp

    @pytest.mark.parametrize(
        ("host", "path", "expected"),
        [
            (
                "http://bking.com",
                "/api",
                "http://bking.com/api",
            ),
            (
                "http://bking.com/",
                "/api",
                "http://bking.com/api",
            ),
            (
                "http://bking.com/",
                "api",
                "http://bking.com/api",
            ),
        ],
    )
    def test_urljoin(self, host, path, expected):
        comp = BaseComponent()
        result = comp._urljoin(host, path)

        assert result == expected
