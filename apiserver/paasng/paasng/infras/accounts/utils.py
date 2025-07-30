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

from typing import Set, Type

from bkpaas_auth import get_user_by_user_id
from django.conf import settings

from paasng.infras.accounts.entities import OauthCredential
from paasng.infras.accounts.models import Oauth2TokenHolder, UserProfile
from paasng.infras.accounts.oauth.backends import get_bkapp_oauth_backend_cls
from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.platform.applications.models import Application
from paasng.platform.sourcectl.models import GitProject


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


def get_oauth_credential(
    source_type: str, user_id: str, mode: str = "default", repo_url: str | None = None
) -> OauthCredential:
    """获取 OAuth 凭证的统一入口函数

    :param source_type: 源码仓库类型，如 gitlab
    :param user_id: 用户 ID，用于查询用户对应的授权凭证
    :param mode: 凭证获取模式，可选值：
        - 'default': 获取第一个可用凭证（原 get_oauth_credentials）
        - 'repo': 根据仓库地址获取精确匹配凭证（原 get_oauth_credential_by_repo）
        - 'user': 获取用户级别 scope 的凭证（原 get_oauth_credential_by_user）
    :param repo_url: 可选，当 mode='repo' 时必须提供，仓库地址
    :raises: Oauth2TokenHolder.DoesNotExist 当凭证不存在时
    """
    try:
        profile = UserProfile.objects.get(user=user_id)
    except UserProfile.DoesNotExist:
        raise Oauth2TokenHolder.DoesNotExist

    if mode == "repo":
        if not repo_url:
            raise ValueError("repo_url is required when mode='repo'")
        project = GitProject.parse_from_repo_url(repo_url, sourcectl_type=source_type)
        token_holder = profile.token_holder.get_by_project(project)
        return OauthCredential(token_holder.access_token, [token_holder.get_scope()])

    if mode == "user":
        token_holder = profile.token_holder.filter_user_scope(source_type)
        return OauthCredential(token_holder.access_token, [token_holder.get_scope()])

    # 默认模式：获取第一个可用凭证
    token_holder_list = profile.token_holder.filter(provider=source_type).all()
    if not token_holder_list:
        raise Oauth2TokenHolder.DoesNotExist
    return OauthCredential(
        oauth_token=token_holder_list[0].access_token, scope_list=[th.get_scope() for th in token_holder_list]
    )


get_oauth_credentials = get_oauth_credential


def get_oauth_credential_by_repo(source_type: str, repo_url: str, user_id: str) -> OauthCredential:
    """根据仓库地址获取对应的 OAuth 凭证
    该函数用于需要精确匹配仓库权限的场景（如创建特定项目组的仓库），会根据仓库地址解析项目信息并匹配 scope 能覆盖该项目的授权凭证。
    例如：授权凭证的 scope 为: group:test1, user:user，创建 groups/test2 项目组下的代码仓库时必须根据要创建的代码仓库地址获取到正确的凭证（user:user）。

    :param source_type: 源码仓库类型
    :param repo_url: 仓库地址（可以是未创建的仓库），用于匹配对应的授权凭证
    :param user_id: 用户 ID
    """
    return get_oauth_credential(source_type, user_id, "repo", repo_url)


def get_oauth_credential_by_user(source_type: str, user_id: str) -> OauthCredential:
    """根据用户 ID 获取用户级别的 OAuth 凭证
    该函数用于需要用户级别权限的场景（如创建用户默认空间下代码仓库），会根据用户 ID 获取用户级别的授权凭证。

    :param source_type: 源码仓库类型
    :param user_id: 用户 ID
    """
    return get_oauth_credential(source_type, user_id, "user")
