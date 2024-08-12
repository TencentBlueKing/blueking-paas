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
from blue_krill.web.std_error import APIError

from paasng.accessories.cloudapi import views
from paasng.misc.audit.constants import OperationEnum
from paasng.platform.applications.models import Application
from tests.utils.testing import get_response_json

pytestmark = pytest.mark.django_db


class TestCloudAPIViewSet:
    @pytest.mark.parametrize(
        ("app_code", "path", "mocked_result"),
        [
            (
                "test",
                "/api/cloudapi/apps/test/apis/",
                {"code": 0},
            ),
        ],
    )
    def test_get(self, request_factory, mocker, app_code, path, mocked_result):
        mocker.patch(
            "paasng.accessories.cloudapi.views.CloudAPIViewSet.permission_classes",
            new_callback=mock.PropertyMock(return_value=None),
        )
        mocker.patch(
            "paasng.accessories.cloudapi.views.get_user_auth_type",
            return_value="test",
        )
        mocker.patch(
            "paasng.accessories.cloudapi.views.bk_apigateway_inner_component.get",
            return_value=mocked_result,
        )

        app, _ = Application.objects.get_or_create(code=app_code)
        request = request_factory.get(path, params={"test": 1})

        view = views.CloudAPIViewSet.as_view({"get": "_get"})
        response = view(
            request,
            apigw_url=views.CloudAPIViewSet._trans_request_path_to_apigw_url(path, app.code),
            app=app,
        )
        result = get_response_json(response)
        assert result == mocked_result

    @pytest.mark.parametrize(
        ("app_code", "operation_type", "path", "mocked_result"),
        [
            (
                "test",
                OperationEnum.APPLY,
                "/api/cloudapi/apps/test/apis/",
                {"code": 0},
            ),
        ],
    )
    def test_post(self, request_factory, mocker, app_code, operation_type, path, mocked_result):
        mocker.patch(
            "paasng.accessories.cloudapi.views.CloudAPIViewSet.permission_classes",
            new_callback=mock.PropertyMock(return_value=None),
        )
        mocker.patch(
            "paasng.accessories.cloudapi.views.get_user_auth_type",
            return_value="test",
        )
        mocker.patch(
            "paasng.accessories.cloudapi.views.bk_apigateway_inner_component.post",
            return_value=mocked_result,
        )

        app, _ = Application.objects.get_or_create(code=app_code)
        request = request_factory.post(path, params={"test": 1})

        view = views.CloudAPIViewSet.as_view({"post": "_post"})
        response = view(
            request,
            apigw_url=views.CloudAPIViewSet._trans_request_path_to_apigw_url(path, app.code),
            operation_type=operation_type,
            app=app,
        )
        result = get_response_json(response)
        assert result == mocked_result

    @pytest.mark.parametrize(
        ("path", "app_code", "expected", "will_error"),
        [
            (
                "/api/cloudapi/apps/test/apis/",
                "test",
                "/api/v1/apis/",
                False,
            ),
            (
                "/api/apps/test/apis/",
                "test",
                None,
                True,
            ),
        ],
    )
    def test_get_bk_apigateway_inner_api_path(self, path, app_code, expected, will_error):
        viewset = views.CloudAPIViewSet()
        if will_error:
            with pytest.raises(APIError):
                viewset._trans_request_path_to_apigw_url(path, app_code)

            return

        result = viewset._trans_request_path_to_apigw_url(path, app_code)
        assert result == expected
