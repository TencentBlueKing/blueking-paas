# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging

from django.conf import settings
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import trans_real as trans
from whitenoise.middleware import WhiteNoiseMiddleware

logger = logging.getLogger(__name__)


class WhiteNoiseRespectPrefixMiddleware(WhiteNoiseMiddleware):
    """Hack WhiteNoise middleware to respect FORCE_SCRIPT_NAME"""

    def process_request(self, request):
        # Prepend FORCE_SCRIPT_NAME to fix bug when service running under an sub-path
        if settings.FORCE_SCRIPT_NAME:
            path_info = settings.FORCE_SCRIPT_NAME + request.path_info
        else:
            path_info = request.path_info

        if self.autorefresh:
            static_file = self.find_file(path_info)
        else:
            static_file = self.files.get(path_info)
        if static_file is not None:
            return self.serve(static_file, request)


class AutoDisableCSRFMiddleware:
    """Disable CSRF checks on purpose"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # When current request was authenticated by bk_paas's non-cookie middleware(# eg. API
        # gateway JWT Token), below attribute will be set to True.
        # For those requests, It's required to disable CSRF check because them do not contain any
        # CSRF token cookies.
        if getattr(request, "_bkpaas_auth_authenticated_from_non_cookies", False):
            request._dont_enforce_csrf_checks = True

        # A setting to disable CSRF check entirely, useful for local development
        if getattr(settings, "DEBUG_FORCE_DISABLE_CSRF", False):
            request._dont_enforce_csrf_checks = True
        return self.get_response(request)

    def process_view(self, request, view, args, kwargs):
        # DRF SessionAuthentication authenticates the user and checks the CSRF again,
        # not recognising the csrf_exempt exemption
        # DRF's CSRF checks behave in the same way as the CsrfViewMiddleware and need to be skipped by
        # setting request._dont_enforce_csrf_checks = True.
        if getattr(view, "csrf_exempt", False):
            request._dont_enforce_csrf_checks = True
        return None


class APILanguageMiddleware(MiddlewareMixin):
    """Set the language for API requests"""

    def process_request(self, request):
        # The current request for the system API authenticated by bk_paas's non-cookie middleware (# eg.
        # API gateway JWT Token) will obtain the language information from the request header
        full_path = request.get_full_path()
        is_sys_url = full_path.startswith(settings.SITE_URL + "sys/api/")

        if is_sys_url and getattr(request, "_bkpaas_auth_authenticated_from_non_cookies", False):
            language = request.META.get("HTTP_BLUEKING_LANGUAGE", settings.LANGUAGE_CODE)
            try:
                language = trans.get_supported_language_variant(language)
            except LookupError:
                logger.warning("The language %s is not supported. ", language)
                language = settings.LANGUAGE_CODE

            if language:
                translation.activate(language)
                request.LANGUAGE_CODE = translation.get_language()
