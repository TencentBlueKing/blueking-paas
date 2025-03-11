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

from bkpaas_auth.models import DatabaseUser
from django.conf import settings
from django.contrib import auth
from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext as _

from paasng.utils.local import local

from .models import User
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
