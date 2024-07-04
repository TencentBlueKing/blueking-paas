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

import pytest

from paasng.accessories.cloudapi.components.bk_apigateway_inner import BkApigatewayInnerComponent


class TestBkApigatewayInnerComponent:
    @pytest.mark.parametrize(
        ("fake_language", "expected"),
        [
            (
                None,
                {
                    "x-bkapi-authorization": json.dumps(
                        {
                            "bk_app_code": "test",
                            "bk_app_secret": "app-secret",
                            "bk_username": "admin",
                        }
                    )
                },
            ),
            (
                "en",
                {
                    "Accept-Language": "en",
                    "x-bkapi-authorization": json.dumps(
                        {
                            "bk_app_code": "test",
                            "bk_app_secret": "app-secret",
                            "bk_username": "admin",
                        }
                    ),
                },
            ),
        ],
    )
    def test_prepare_headers(self, settings, mocker, fake_language, expected):
        settings.BK_APP_CODE = "test"
        settings.BK_APP_SECRET = "app-secret"

        mocker.patch(
            "paasng.accessories.cloudapi.components.bk_apigateway_inner.get_language",
            return_value=fake_language,
        )

        comp = BkApigatewayInnerComponent()
        result = comp._prepare_headers("admin")

        assert result == expected
