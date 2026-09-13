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

from unittest import mock

import pytest

from paasng.infras.iam.base.backends import BaseAuthBackend
from paasng.infras.iam.base.dto import ActionRequest, AuthResource
from paasng.infras.iam.permissions.client import IAMClient
from paasng.infras.iam.permissions.resources.application import AppAction, ApplicationPermission
from paasng.infras.iam.v3.apigw.client import Client as BKIAMV3GatewayClient
from paasng.infras.iam.v4.apigw.client import Client as BKIAMV4GatewayClient


@pytest.fixture()
def mocked_backend():
    """替换门面背后的鉴权实现，验证调用被原样转发"""
    backend = mock.Mock(spec=BaseAuthBackend)
    with mock.patch.object(IAMClient, "_get_auth_backend", return_value=backend):
        yield backend


class TestFacadeDelegation:
    """门面须将调用原样转发给分发到的实现，使上层调用方无需感知版本差异"""

    def test_resource_type_allowed(self, mocked_backend):
        IAMClient().resource_type_allowed("user-0", "tenant-foo", AppAction.VIEW_BASIC_INFO)

        mocked_backend.resource_type_allowed.assert_called_once_with(
            "user-0", "tenant-foo", AppAction.VIEW_BASIC_INFO, False
        )

    def test_resource_inst_allowed(self, mocked_backend):
        resources = [AuthResource("bk_paas3", "application", "app-code")]

        IAMClient().resource_inst_allowed("user-0", "tenant-foo", AppAction.VIEW_BASIC_INFO, resources, True)

        mocked_backend.resource_inst_allowed.assert_called_once_with(
            "user-0", "tenant-foo", AppAction.VIEW_BASIC_INFO, resources, True
        )

    def test_resource_inst_multi_actions_allowed(self, mocked_backend):
        IAMClient().resource_inst_multi_actions_allowed("user-0", "tenant-foo", ["view_basic_info"], [])

        mocked_backend.resource_inst_multi_actions_allowed.assert_called_once_with(
            "user-0", "tenant-foo", ["view_basic_info"], []
        )

    def test_batch_resource_multi_actions_allowed(self, mocked_backend):
        IAMClient().batch_resource_multi_actions_allowed("user-0", "tenant-foo", ["view_basic_info"], [])

        mocked_backend.batch_resource_multi_actions_allowed.assert_called_once_with(
            "user-0", "tenant-foo", ["view_basic_info"], []
        )

    def test_build_resource_filter(self, mocked_backend):
        key_mapping = {"application.id": "code"}

        IAMClient().build_resource_filter("user-0", "tenant-foo", AppAction.VIEW_BASIC_INFO, key_mapping)

        mocked_backend.build_resource_filter.assert_called_once_with(
            "user-0", "tenant-foo", AppAction.VIEW_BASIC_INFO, key_mapping
        )

    def test_build_apply_url(self, mocked_backend):
        action_requests = [ActionRequest(AppAction.VIEW_BASIC_INFO, "application", ["app-code"])]

        IAMClient().build_apply_url("tenant-foo", action_requests)

        mocked_backend.build_apply_url.assert_called_once_with("tenant-foo", action_requests)


class TestPermissionFollowsVersion:
    """列表策略下推经门面分发，不再直连 V3 SDK"""

    def test_app_filters_go_through_facade(self, mocked_backend):
        mocked_backend.build_resource_filter.return_value = None

        ApplicationPermission().gen_user_app_filters("user-0", "tenant-foo")

        assert mocked_backend.build_resource_filter.call_args.args[2] == AppAction.VIEW_BASIC_INFO

    def test_develop_app_filters_use_develop_action(self, mocked_backend):
        mocked_backend.build_resource_filter.return_value = None

        ApplicationPermission().gen_develop_app_filters("user-0", "tenant-foo")

        assert mocked_backend.build_resource_filter.call_args.args[2] == AppAction.BASIC_DEVELOP


class TestGatewayIsolation:
    def test_v3_and_v4_use_different_gateways(self):
        """V3 与 V4 是两个独立网关，可据此从访问日志确认请求实际打到了哪个版本"""
        assert BKIAMV3GatewayClient._api_name == "bk-iam"
        assert BKIAMV4GatewayClient._api_name == "bkiam"
