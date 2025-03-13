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

from typing import List, Type

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from paasng.bk_plugins.pluginscenter.iam_adaptor.constants import PluginPermissionActions
from paasng.bk_plugins.pluginscenter.iam_adaptor.definitions import gen_iam_resource
from paasng.bk_plugins.pluginscenter.iam_adaptor.management.shim import user_group_apply_url
from paasng.bk_plugins.pluginscenter.iam_adaptor.policy.client import lazy_iam_client
from paasng.bk_plugins.pluginscenter.models import PluginInstance


def plugin_action_permission_class(actions: List[PluginPermissionActions], use_cache: bool = False):
    class PluginActionPermission(BasePermission):
        @property
        def message(self):
            return _("用户无以下权限 {actions}").format(
                actions=[PluginPermissionActions.get_choice_label(action) for action in actions]
            )

        def has_object_permission(self, request, view, obj):
            if not isinstance(obj, PluginInstance):
                return False

            iam_resource = gen_iam_resource(obj)
            if len(actions) == 1:
                is_allowed = lazy_iam_client.is_action_allowed(
                    request.user.username, actions[0], [iam_resource], use_cache=use_cache
                )
            else:
                is_allowed = all(
                    lazy_iam_client.is_actions_allowed(request.user.username, actions, [iam_resource]).values()
                )
            # 无插件应用权限时，需要返回应用权限申请链接
            if not is_allowed:
                raise PermissionDenied({"message": self.message, **user_group_apply_url(obj.id)})

            return True

    return PluginActionPermission


def plugin_view_actions_perm(
    view_action_map: dict[str, list[PluginPermissionActions]],
    default_actions: list[PluginPermissionActions] | None = None,
    use_cache: bool = False,
) -> Type[BasePermission]:
    """Create a permission class for plugin view, it allows using different action(s)
    for different view actions.

    :param view_action_map: A map from view action to plugin actions.
    :param default_action: Optional, the default action if the view action
        is not found.
    :return: A permission class.
    """

    class PluginActionPermission(BasePermission):
        """The permission class for plugin views."""

        @property
        def message(self):
            return _("用户无权限执行此操作")

        def has_object_permission(self, request, view, obj):
            if not isinstance(obj, PluginInstance):
                return False

            # Get the actions from the view action map, if not found, use the default actions.
            actions = view_action_map.get(view.action, default_actions)
            if actions is None:
                raise ValueError('No plugin actions found for view action "%s".' % view.action)

            iam_resource = gen_iam_resource(obj)
            if len(actions) == 1:
                is_allowed = lazy_iam_client.is_action_allowed(
                    request.user.username, actions[0], [iam_resource], use_cache=use_cache
                )
            else:
                is_allowed = all(
                    lazy_iam_client.is_actions_allowed(request.user.username, actions, [iam_resource]).values()
                )
            # 无插件应用权限时，需要返回应用权限申请链接
            if not is_allowed:
                message = _("用户无以下权限 {actions}").format(
                    actions=[PluginPermissionActions.get_choice_label(action) for action in actions]
                )
                raise PermissionDenied({"message": message, **user_group_apply_url(obj.id)})

            return True

    return PluginActionPermission
