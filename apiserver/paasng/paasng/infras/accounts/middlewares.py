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

import json
import logging
from typing import Callable, Optional

from bkpaas_auth.models import DatabaseUser
from blue_krill.auth.utils import validate_jwt_token
from django.conf import settings
from django.contrib import auth
from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils.encoding import smart_str
from django.utils.translation import gettext as _
from rest_framework.authentication import get_authorization_header

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.utils import ForceAllowAuthedApp
from paasng.utils.basic import get_client_ip
from paasng.utils.local import local

from .models import AuthenticatedAppAsUser, User, UserPrivateToken, UserProfile
from .permissions.constants import SiteAction
from .permissions.global_site import user_has_site_action_perm

logger = logging.getLogger(__name__)


class SiteAccessControlMiddleware(MiddlewareMixin):
    """Control who can visit which paths in macro way"""

    def process_request(self, request):
        # Ignore anonymous user
        if not request.user.is_authenticated:
            return None

        if not user_has_site_action_perm(request.user, SiteAction.VISIT_SITE):
            # Use a custom
            return JsonResponse(
                {"code": "PRODUCT_NOT_READY", "detail": _("产品灰度测试中，尚未开放，敬请期待")}, status=404
            )
        return None


class PrivateTokenAuthenticationMiddleware:
    """Authenticate user by private token"""

    AUTH_HEADER_TYPE = "Bearer"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = self.get_user(request)
        if user:
            logger.info(
                "Authenticated user by PrivateToken, username: %s, ip: %s, path: %s",
                user.username,
                get_client_ip(request),
                request.path_info,
            )
            set_database_user(request, user)

        response = self.get_response(request)
        return response

    def get_user(self, request) -> Optional[User]:
        """Get user object from current request"""
        token_string = self.get_token_string(request)
        # Ignore empty or JWT format token
        if not token_string or validate_jwt_token(token_string):
            return None
        try:
            token_obj = UserPrivateToken.objects.get(token=token_string)
        except UserPrivateToken.DoesNotExist:
            logger.warning(f"private token {token_string} does not exist in database")
            return None

        if token_obj.has_expired():
            logger.warning(f"private token {token_string} has expired")
            return None

        logger.debug(f"private token {token_string} is valid, user is {token_obj.user.username}")
        return token_obj.user

    def get_token_string(self, request) -> Optional[str]:
        """Get private token string from current request"""
        # Source: query string
        token_from_qs = request.GET.get("private_token", None)
        if token_from_qs:
            return token_from_qs

        # Source: Authorization header
        token_from_header = self.get_token_string_from_header(request)
        if token_from_header:
            return token_from_header

        return None

    def get_token_string_from_header(self, request) -> Optional[str]:
        """Get private token string from current request header"""
        auth = get_authorization_header(request).split()
        # Turn bytestring into str
        auth = [smart_str(s) for s in auth]

        if not auth or auth[0].lower() != self.AUTH_HEADER_TYPE.lower():
            return None

        if len(auth) == 1:
            logger.warning("Invalid token header. No private token provided.")
            return None
        elif len(auth) > 2:
            logger.warning("Invalid token header. Token string should not contain spaces.")
            return None
        return auth[1]


class AuthenticatedAppAsUserMiddleware:
    """When an API request forwarded by API Gateway was received, if it includes an authenticated
    app(aka "OAuth client") and has no authenticated user info too, this middleware will try to attach
    an authenticated user object to current request according to the app info.

    If other services want to call apiserver's SYSTEM APIs, this middleware can be very useful.
    Under these circumstances, a valid "app_code/app_secret" pair usually was already provided in every
    request, if "app_code" was configured in `AuthenticatedAppAsUser`, no extra credentials were
    needed in order to make a authenticated request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Ignore already authenticated requests
        if getattr(request, "user", None) and request.user.is_authenticated:
            return

        if user := self.get_user(request, view_func):
            logger.info(
                "Authenticated user by AuthenticatedApp, username: %s, ip: %s, path: %s",
                user.username,
                get_client_ip(request),
                request.path_info,
            )
            set_database_user(request, user)
        return

    def get_user(self, request, view_func: Callable) -> Optional[User]:
        """Get an user object from current request, if no relation can be found by current
        application, a user and relation might be created if the view object has been marked
        as "force-allow" by `ForceAllowAuthedApp.mark_view_set`.

        :param request: Current request object.
        :param view_func: Current view function.
        :return: An User object.
        """
        if not getattr(request, "app", None):
            return None
        if not request.app.verified:
            return None

        try:
            obj = AuthenticatedAppAsUser.objects.get(bk_app_code=request.app.bk_app_code, is_active=True)
        except AuthenticatedAppAsUser.DoesNotExist:
            if hasattr(view_func, "cls") and ForceAllowAuthedApp.check_marked(view_func.cls):
                # Automatically create a new user and relation
                return self.create_user(request.app.bk_app_code)
            return None
        else:
            return obj.user

    @staticmethod
    def create_user(bk_app_code: str) -> DatabaseUser:
        """Create a user and relationship from an application code with default permissions."""
        # Create the user
        user_db, _ = User.objects.get_or_create(username=f"authed-app-{bk_app_code}")
        user = DatabaseUser.from_db_obj(user_db)
        UserProfile.objects.update_or_create(user=user.pk, defaults={"role": SiteRole.SYSTEM_API_BASIC_READER.value})

        # Create the relationship
        AuthenticatedAppAsUser.objects.update_or_create(
            bk_app_code=bk_app_code, defaults={"user": user_db, "is_active": True}
        )
        return user_db


class RequestIDProvider:
    """向 request，response 注入 request_id"""

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        local.request = request
        request.request_id = local.get_http_request_id()

        response = self.get_response(request)
        response[settings.REQUEST_ID_HEADER_KEY] = request.request_id

        local.release()
        return response


class WrapUsernameAsUserMiddleware:
    """用于免用户认证的 apigw 接口, 将头部获取的 bk_username 包装成 request 的 user 对象.

    Note: 配置在 apigw_manager.apigw.authentication.ApiGatewayJWTAppMiddleware 后面
    """

    BKPAASAPI_AUTHORIZATION_META_KEY = "HTTP_X_BKPAASAPI_AUTHORIZATION"

    def __init__(self, get_response):
        self.get_response = get_response

    def get_user(self, request, gateway_name=None, bk_username=None, verified=False, **credentials):
        return auth.authenticate(
            request, gateway_name=gateway_name, bk_username=bk_username, verified=verified, **credentials
        )

    def __call__(self, request):
        jwt_info = getattr(request, "jwt", None)
        if not jwt_info:
            return self.get_response(request)

        req_app = getattr(request, "app", None)
        if not req_app:
            return self.get_response(request)

        if user_data := request.META.get(self.BKPAASAPI_AUTHORIZATION_META_KEY):
            # TODO 增加 api_name 和 app_code 的白名单校验?
            try:
                bk_username = json.loads(user_data).get("bk_username")
            except json.decoder.JSONDecodeError:
                logger.warning(f"Invalid auth header: {user_data}")
            else:
                if bk_username:
                    request.user = self.get_user(
                        request,
                        gateway_name=jwt_info.gateway_name,
                        bk_username=bk_username,
                        verified=req_app.verified,
                    )
        return self.get_response(request)


def set_database_user(request: HttpRequest, user: User, set_non_cookies: bool = True):
    """Mark current request authenticated with a user stored in database

    :param user: a `models.User` object
    :param set_non_cookies: whether set a special attribute to mark current request was NOT authenticated
        via user cookies.
    """
    # Translate the user into module "bkpaas_auth"'s User object to maintain consistency.
    request.user = DatabaseUser.from_db_obj(user=user)
    if set_non_cookies:
        # Reference from bkpaas_auth
        # Set a special attribute on request to mark this user was not authenticated from
        # cookie, so we may apply other logics afterwards, such as skipping CSRF checks.
        setattr(request, "_bkpaas_auth_authenticated_from_non_cookies", True)
