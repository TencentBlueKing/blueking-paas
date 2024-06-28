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

from unittest import mock

import pytest


def _mock_initialize_vcs_with_template():
    with mock.patch(
        "paasng.platform.modules.manager.ModuleInitializer.initialize_vcs_with_template"
    ) as initialize_with_template:
        initialize_with_template.return_value = {}
        yield initialize_with_template


mock_initialize_vcs_with_template = pytest.fixture(_mock_initialize_vcs_with_template)


class FakeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


@pytest.fixture(autouse=True)
def _mock_bkpaas_auth_middlewares():
    with mock.patch("bkpaas_auth.middlewares.CookieLoginMiddleware", new=FakeMiddleware), mock.patch(
        "apigw_manager.apigw.authentication.ApiGatewayJWTGenericMiddleware", new=FakeMiddleware
    ), mock.patch("apigw_manager.apigw.authentication.ApiGatewayJWTUserMiddleware", new=FakeMiddleware), mock.patch(
        "apigw_manager.apigw.authentication.ApiGatewayJWTUserMiddleware", new=FakeMiddleware
    ):
        yield
