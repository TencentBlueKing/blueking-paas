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

import logging
import time
from typing import Dict, Optional, Type, Union

from django.conf import settings
from iam.exceptions import AuthAPIError
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from paasng.infras.iam.helpers import user_group_apply_url
from paasng.infras.iam.permissions.resources.application import AppAction, ApplicationPermission, AppPermCtx
from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module
from paasng.utils.basic import get_username_by_bkpaas_user_id

logger = logging.getLogger(__name__)


class BaseAppPermission(BasePermission):
    """The base class for application permission. It doesn't provide any functionality
    yet but it can be useful for other modules to check the permission type.
    """


def application_perm_class(action: AppAction) -> Type[BasePermission]:
    """构建 DRF 可用的应用权限类

    :param action: Application operation type.
    :return: Application permission class.
    """

    class AppModulePermission(BaseAppPermission):
        """The permission class for application and module."""

        def has_object_permission(self, request, view, obj: Union[Application, Module]):
            """Check if the current request has permission to operate the object.
            If the object type is not supported, return `false`.
            """
            if isinstance(obj, Application):
                return user_has_app_action_perm(request.user, obj, action)
            elif isinstance(obj, Module):
                return user_has_app_action_perm(request.user, obj.application, action)
            else:
                raise TypeError(f"Permission check on incorrect type: {type(obj)}")

    return AppModulePermission


def app_view_actions_perm(
    view_action_map: Dict[str, AppAction], default_action: Optional[AppAction] = None
) -> Type[BasePermission]:
    """Create a permission class for application view, it allows using different
    application action for different view actions.

    :param view_action_map: A map from view action to application action.
    :param default_action: Optional, the default application action if the view action
        is not found.
    :return: Application permission class.
    """

    class AppViewActionsPermission(BaseAppPermission):
        """The permission class for application and module."""

        def has_object_permission(self, request, view, obj: Union[Application, Module]):
            # Get the action from the view action map, if not found, use the default action.
            action = view_action_map.get(view.action, default_action)
            if not action:
                raise ValueError('No app action found for view action "%s".' % view.action)

            if isinstance(obj, Application):
                return user_has_app_action_perm(request.user, obj, action)
            elif isinstance(obj, Module):
                return user_has_app_action_perm(request.user, obj.application, action)
            else:
                raise TypeError(f"Permission check on incorrect type: {type(obj)}")

    return AppViewActionsPermission


def check_application_perm(user, application: Application, action: AppAction):
    """检查指定用户是否对应用的某个操作具有权限。"""
    if not user_has_app_action_perm(user, application, action):
        raise PermissionDenied(
            {"message": "You are not allowed to do this operation.", **user_group_apply_url(application.code)}
        )


def can_exempt_application_perm(user, application: Application) -> bool:
    # 由于权限中心的用户组授权为异步行为，即创建用户组，添加用户，对组授权后需要等待一段时间（10-20秒左右）才能鉴权
    # 因此需要在应用创建后的一定的时间内，对创建者（拥有应用最高权限）的操作进行权限豁免以保证功能可正常使用
    return (
        user.pk == application.owner
        and time.time() - application.created.timestamp() < settings.IAM_PERM_EFFECTIVE_TIMEDELTA
    )


def user_has_app_action_perm(user, application: Application, action: AppAction) -> bool:
    """
    检查指定用户是否对应用的某个操作具有权限

    # TODO 如果后续需要支持 无权限跳转权限中心申请，可以设置 raise_exception = True，PermissionDeniedError 会包含 apply_url 信息
    """
    if can_exempt_application_perm(user, application):
        return True

    perm_ctx = AppPermCtx(
        code=application.code,
        username=get_username_by_bkpaas_user_id(user.pk),
    )
    try:
        return ApplicationPermission().get_method_by_action(action)(perm_ctx, raise_exception=False)
    except AuthAPIError:
        logger.exception("check user has application perm error.")

    return False
