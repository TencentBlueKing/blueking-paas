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

from typing import List

import pytest
from rest_framework.decorators import APIView
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from paasng.bk_plugins.pluginscenter.iam_adaptor.constants import PluginPermissionActions
from paasng.bk_plugins.pluginscenter.iam_adaptor.policy.permissions import plugin_action_permission_class

pytestmark = pytest.mark.django_db


def make_view(plugin, actions: List[PluginPermissionActions]):
    class DummyView(APIView):
        permission_classes = [plugin_action_permission_class(actions)]

        def get(self, request):
            self.check_object_permissions(request, plugin)
            return Response()

    return DummyView.as_view()


@pytest.fixture()
def drf_request(bk_user):
    request = APIRequestFactory().request()
    request.user = bk_user
    return request


class TestPermission:
    @pytest.mark.parametrize(
        "action", [PluginPermissionActions.BASIC_DEVELOPMENT, PluginPermissionActions.MANAGE_CONFIGURATION]
    )
    def test_single_action(self, plugin_with_role, drf_request, iam_policy_client, action):
        iam_policy_client.is_action_allowed.return_value = False
        response = make_view(plugin_with_role, [action])(drf_request)
        assert response.status_code == 403
        assert response.data["message"] == "用户无以下权限 {actions}".format(
            actions=[PluginPermissionActions.get_choice_label(action)]
        )

        iam_policy_client.is_action_allowed.return_value = True
        response = make_view(plugin_with_role, [action])(drf_request)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        ("actions_permission", "status_code"),
        [
            (
                {
                    PluginPermissionActions.EDIT_PLUGIN: False,
                    PluginPermissionActions.DELETE_PLUGIN: True,
                },
                403,
            ),
            (
                {
                    PluginPermissionActions.EDIT_PLUGIN: False,
                    PluginPermissionActions.DELETE_PLUGIN: False,
                },
                403,
            ),
            (
                {
                    PluginPermissionActions.EDIT_PLUGIN: True,
                    PluginPermissionActions.DELETE_PLUGIN: True,
                },
                200,
            ),
        ],
    )
    def test_multi_actions(self, plugin_with_role, drf_request, iam_policy_client, actions_permission, status_code):
        iam_policy_client.is_actions_allowed.return_value = actions_permission
        response = make_view(plugin_with_role, list(actions_permission.keys()))(drf_request)
        assert response.status_code == status_code
