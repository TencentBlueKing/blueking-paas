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
import re
from typing import Dict

from blue_krill.auth.jwt import ClientJWTAuth, JWTAuthConf
from django.conf import settings
from django.http import Http404
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.shortcuts import redirect
from revproxy.views import ProxyView

from paasng.utils.views import make_unauthorized_json

from .plugins import get_current_instances
from .response import get_django_response

# The "role" for signing JWT token
JWT_ROLE_PROXY = 'service-proxy'

ALLOWED_PATH_PATTERNS = (
    re.compile('^api/scheduling/'),
    re.compile('^api/services/'),
    re.compile('^api/processes/'),
    re.compile('^api/cnative/'),
    re.compile('^api/credentials/'),
    re.compile('^admin42/'),
    re.compile('^metrics$'),
)


class SvcWorkloadsView(ProxyView):
    """Proxy requests for workloads service"""

    add_remote_user = True
    upstream = settings.ENGINE_CONTROLLER_HOST

    def dispatch(self, request, path):
        if not self.check_path(path):
            raise Http404

        self.request_headers = self.get_request_headers()
        self._extra_setup_headers(request, path)

        redirect_to = self._format_path_to_redirect(request)
        if redirect_to:
            return redirect(redirect_to)

        proxy_response = self._created_proxy_response(request, path)

        self._replace_host_on_redirect_location(request, proxy_response)
        self._set_content_type(request, proxy_response)

        response = get_django_response(proxy_response, strict_cookies=self.strict_cookies)

        # When response is in JSON format and status code is "401 authorized", replace the response with
        # another JSON to provide extra "login URLs"
        content_type = response.get('Content-Type')
        if content_type == 'application/json' and response.status_code == 401:
            return JsonResponse(make_unauthorized_json(), status=401)

        self.log.debug("RESPONSE RETURNED: %s", response)
        return response

    @staticmethod
    def check_path(path: str) -> bool:
        """Check if path is allowed for proxy, use whitelist to protect system-level APIs"""
        if any(pattern.search(path) for pattern in ALLOWED_PATH_PATTERNS):
            return True
        return False

    def _extra_setup_headers(self, request: HttpRequest, path: str):
        """Do some extra setup jobs after assembling request.headers"""
        current_user_pk = request.user.pk
        extra_payload = {'current_user_pk': current_user_pk}

        # Run extra plugins, set extra information in payload, which includes:
        #
        # - current application info, if request.path matchs pattern
        # - user's permissions on current application, when application info is presented
        extra_payload['insts'] = get_current_instances(request.user, path)

        # All extra info will be written into JWT token
        self.request_headers['Authorization'] = self._make_serives_auth_header(extra_payload)

    def _make_serives_auth_header(self, extra_payload: Dict) -> str:
        """Make a JWT token for authenticating between services"""
        conf_map = settings.INTERNAL_SERVICES_JWT_AUTH_CONF
        conf = JWTAuthConf(
            iss=conf_map['iss'],
            key=conf_map['key'],
            role=JWT_ROLE_PROXY,
        )
        return ClientJWTAuth(conf).make_authorization_header_value(extra_payload)
