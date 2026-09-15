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
from django.db.models import Q

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
        resource = AuthResource("bk_paas3", "application", "app-code")

        IAMClient().resource_inst_allowed("user-0", "tenant-foo", AppAction.VIEW_BASIC_INFO, resource, True)

        mocked_backend.resource_inst_allowed.assert_called_once_with(
            "user-0", "tenant-foo", AppAction.VIEW_BASIC_INFO, resource, True
        )

    def test_resource_inst_multi_actions_allowed(self, mocked_backend):
        resource = AuthResource("bk_paas3", "application", "app-code")

        IAMClient().resource_inst_multi_actions_allowed("user-0", "tenant-foo", ["view_basic_info"], resource)

        mocked_backend.resource_inst_multi_actions_allowed.assert_called_once_with(
            "user-0", "tenant-foo", ["view_basic_info"], resource
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


class TestAppFiltersComposition:
    """`_gen_app_filters` 如何把权限条件、租户条件与豁免窗口组合成列表查询的过滤器

    断言 Q 的结构而不是编译出的 SQL：条件进不进 WHERE 是 Django 的事，我们要守的是组合
    方式。而 SQL 文本里「出现过 tenant_id」区分不了 `权限 AND 租户` 与 `权限 OR 租户`，
    后者会让恒真的通配符条件放通所有租户的应用。
    """

    @staticmethod
    def _permission_branch(filters: Q) -> Q:
        """取出 `_gen_app_filters` 产出的权限分支

        它的形状是 `(权限条件 & 租户条件) | 豁免窗口`，即顶层 OR 的第一个子节点。
        """
        assert filters.connector == Q.OR, f"顶层应为 OR（权限分支与豁免窗口并列），实际是 {filters.connector}"
        return filters.children[0]

    def test_permission_is_anded_with_tenant(self, mocked_backend):
        """具体实例授权时，权限条件与租户条件必须是 AND

        改成 OR 会让任一条件单独成立即可见，直接造成跨租户越权。
        """
        mocked_backend.build_resource_filter.return_value = Q(code__in=["app-foo", "app-bar"])

        branch = self._permission_branch(ApplicationPermission().gen_user_app_filters("user-0", "tenant-foo"))

        assert branch.connector == Q.AND
        assert ("code__in", ["app-foo", "app-bar"]) in branch.children
        assert ("tenant_id", "tenant-foo") in branch.children

    def test_wildcard_is_treated_as_a_policy(self, mocked_backend):
        """通配符条件要被当成有效策略，而不是落进「未取得策略」分支

        `_gen_app_filters` 用 `if not filters` 判断有无策略，所以「全部可见」必须由一个
        truthy 的恒真条件表达；若实现改成返回空 Q()，这里会退到只剩豁免窗口。
        """
        mocked_backend.build_resource_filter.return_value = ~Q(pk=None)

        branch = self._permission_branch(ApplicationPermission().gen_user_app_filters("user-0", "tenant-foo"))

        assert ~Q(pk=None) in branch.children

    def test_no_policy_falls_back_to_exempt_window_only(self, mocked_backend):
        """未取得策略时只剩豁免窗口条件，不产出无过滤的全量查询"""
        mocked_backend.build_resource_filter.return_value = None

        filters = ApplicationPermission().gen_user_app_filters("user-0", "tenant-foo")

        # 没有权限分支可并列，顶层直接就是豁免窗口本身
        assert filters.connector == Q.AND
        # 豁免窗口限定为「本人创建且在时间窗内」，两个条件缺一都会放宽可见范围
        field_names = {child[0] for child in filters.children if isinstance(child, tuple)}
        assert field_names == {"owner", "created__gt"}


class TestGatewayIsolation:
    def test_v3_and_v4_use_different_gateways(self):
        """V3 与 V4 是两个独立网关，可据此从访问日志确认请求实际打到了哪个版本"""
        assert BKIAMV3GatewayClient._api_name == "bk-iam"
        assert BKIAMV4GatewayClient._api_name == "bkiam"
