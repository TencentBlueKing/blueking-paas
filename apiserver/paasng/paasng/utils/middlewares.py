# -*- coding: utf-8 -*-
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
from django.conf import settings
from whitenoise.middleware import WhiteNoiseMiddleware


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
        if getattr(request, '_bkpaas_auth_authenticated_from_non_cookies', False):
            request._dont_enforce_csrf_checks = True

        # A setting to disable CSRF check entirely, useful for local development
        if getattr(settings, 'DEBUG_FORCE_DISABLE_CSRF', False):
            request._dont_enforce_csrf_checks = True
        return self.get_response(request)
