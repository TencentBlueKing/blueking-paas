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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib import auth
from django.http import JsonResponse
from django.utils import timezone as dj_timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext as _

from paasng.utils.local import local

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


class UserTimezoneMiddleware(MiddlewareMixin):
    """按用户的时区属性激活 Django 时区。

    该中间件从用户管理系统获取用户时区信息并激活，使所有时间相关的序列化输出
    都使用用户所在时区的偏移量。

    执行逻辑:
    1. 未登录用户跳过处理
    2. 从 request.user 读取 time_zone 属性
    3. 若时区字段缺失或非法，回退到默认时区 settings.TIME_ZONE
    4. 在响应返回时重置时区，避免线程复用导致的时区污染

    Note: 必须放在所有用户认证中间件之后
    """

    def process_request(self, request):
        # Ignore anonymous user
        if not request.user.is_authenticated:
            return

        user = request.user
        tz_name = getattr(user, "time_zone", None)

        # Try to activate user's timezone if it's a non-empty string
        if tz_name and isinstance(tz_name, str):
            try:
                user_tz = ZoneInfo(tz_name)
                dj_timezone.activate(user_tz)
            except ZoneInfoNotFoundError as e:
                logger.warning(
                    "Invalid time_zone '%s' for user '%s', fallback to default. Error: %s",
                    tz_name,
                    user.username,
                    str(e),
                )
            else:
                logger.debug("Activated timezone '%s' for user '%s'", tz_name, user.username)
                return

        # Fallback to default timezone when time_zone is empty or invalid
        dj_timezone.activate(dj_timezone.get_default_timezone())

    def process_response(self, request, response):
        """重置时区"""
        dj_timezone.deactivate()
        return response
