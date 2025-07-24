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

from typing import Any, Dict, Set, Type

from bkpaas_auth import get_user_by_user_id
from django.conf import settings

from paasng.infras.accounts.models import Oauth2TokenHolder, UserProfile
from paasng.infras.accounts.oauth.backends import get_bkapp_oauth_backend_cls
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.platform.applications.models import Application


def get_user_avatar(username):
    """获取用户头像"""
    try:
        from .utils_ext import get_user_avatar_ext

        return get_user_avatar_ext(username)
    except ImportError:
        return ""


def id_to_username(user_id: str) -> str:
    """Get username by decoding user id"""
    return get_user_by_user_id(user_id, username_only=True).username


class ForceAllowAuthedApp:
    """See `AuthenticatedAppAsClientMiddleware` for related details."""

    _view_sets: Set[Type] = set()

    @classmethod
    def mark_view_set(cls, view_class):
        """Mark a view set"""
        cls._view_sets.add(view_class)
        return view_class

    @classmethod
    def check_marked(cls, view_class) -> bool:
        """Check if a view set has been marked"""
        return view_class in cls._view_sets


def create_app_oauth_backend(application: Application, env_name: str = settings.AUTH_ENV_NAME):
    """使用指定的应用的身份"""
    app_secret = get_oauth2_client_secret(application.code)
    return get_bkapp_oauth_backend_cls()(
        auth_url=settings.TOKEN_AUTH_ENDPOINT,
        refresh_url=settings.TOKEN_REFRESH_ENDPOINT,
        # 借用了 bkpaas-auth 的配置项
        validate_url=settings.BKAUTH_TOKEN_CHECK_ENDPOINT,
        app_code=application.code,
        app_secret=app_secret,
        env_name=env_name,
    )


def get_oauth_credentials(source_control_type: str, user_id: str) -> Dict[str, Any]:
    """获取用户的OAuth凭证用于访问代码仓库

    :param source_control_type: 源码控制类型，如 gitlab
    :param user_id: 用户 ID，用于查询用户对应的授权凭证
    """
    profile = UserProfile.objects.get(user=user_id)
    token_holder_list = profile.token_holder.filter(provider=source_control_type).all()
    if not token_holder_list:
        raise Oauth2TokenHolder.DoesNotExist

    # 使用第一个 token_holder 的 access_token
    token_holder = token_holder_list[0]
    return {
        "oauth_token": token_holder.access_token,
        "scope_list": [th.get_scope() for th in token_holder_list],
    }
