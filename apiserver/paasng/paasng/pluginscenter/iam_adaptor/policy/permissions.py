"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import List

from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission

from paasng.pluginscenter.iam_adaptor.constants import PluginPermissionActions
from paasng.pluginscenter.iam_adaptor.definitions import gen_iam_resource
from paasng.pluginscenter.iam_adaptor.policy.client import lazy_iam_client
from paasng.pluginscenter.models import PluginInstance


def plugin_action_permission_class(actions: List[PluginPermissionActions], use_cache: bool = False):
    class PluginActionPermission(BasePermission):
        @property
        def message(self):
            return _("用户无以下权限 {actions}").format(
                actions=[PluginPermissionActions.get_choice_label(aciton) for aciton in actions]
            )

        def has_object_permission(self, request, view, obj):
            if not isinstance(obj, PluginInstance):
                return False

            iam_resource = gen_iam_resource(obj)
            if len(actions) == 1:
                return lazy_iam_client.is_action_allowed(
                    request.user.username, actions[0], [iam_resource], use_cache=use_cache
                )
            return all(lazy_iam_client.is_actions_allowed(request.user.username, actions, [iam_resource]).values())

    return PluginActionPermission
