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
from functools import wraps

from bkpaas_auth.models import User
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import UserProfile
from paasng.infras.accounts.permissions.constants import PlatMgtAction


def plat_mgt_perm_class(action: PlatMgtAction):
    """构建 DRF 可用的权限类，管理平台管理相关权限"""

    class Permission(BasePermission):
        perm_action = action

        def has_permission(self, request, *args, **kwargs):
            if not user_has_plat_mgt_action_perm(request.user, action):
                raise PermissionDenied("You are not allowed to do this operation.")
            return True

        def has_object_permission(self, request, view, obj):
            if not user_has_plat_mgt_action_perm(request.user, action):
                raise PermissionDenied("You are not allowed to do this operation.")
            return True

    return Permission


def plat_mgt_perm_required(action: PlatMgtAction):
    """平台管理权限验证装饰器"""

    def decorated(func):
        # FIXME（多租户）如何利用 perm_insure 模块来确保权限已被正确配置？

        @wraps(func)
        def view_func(self, request, *args, **kwargs):
            if not user_has_plat_mgt_action_perm(request.user, action):
                raise PermissionDenied("You are not allowed to do this operation.")

            return func(self, request, *args, **kwargs)

        return view_func

    return decorated


def user_has_plat_mgt_action_perm(user: User, action: PlatMgtAction) -> bool:
    """检查指定用户是否有平台管理的权限"""
    if not user.is_authenticated:
        return False

    profile = UserProfile.objects.get_profile(user).first()
    if not profile:
        return False

    # FIXME（多租户）目前暂时使用 SiteRole，后续得切换成新的
    return profile.role in [SiteRole.ADMIN, SiteRole.SUPER_USER]
