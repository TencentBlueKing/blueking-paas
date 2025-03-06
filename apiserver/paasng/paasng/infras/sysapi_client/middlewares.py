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
from typing import Callable, Optional

from blue_krill.auth.utils import validate_jwt_token
from django.http import HttpRequest
from django.utils.encoding import smart_str
from rest_framework.authentication import get_authorization_header

from paasng.infras.accounts.utils import ForceAllowAuthedApp
from paasng.infras.sysapi_client.roles import ClientRole
from paasng.utils.basic import get_client_ip

from .models import AuthenticatedAppAsClient, ClientPrivateToken, SysAPIClient

logger = logging.getLogger(__name__)


class PrivateTokenAuthenticationMiddleware:
    """Authenticate a system api client by private token"""

    AUTH_HEADER_TYPE = "Bearer"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if client := self.get_client(request):
            logger.info(
                "Authenticated sysapi client by PrivateToken, name: %s, ip: %s, path: %s",
                client.name,
                get_client_ip(request),
                request.path_info,
            )
            set_sysapi_client(request, client)

        response = self.get_response(request)
        return response

    def get_client(self, request) -> SysAPIClient | None:
        """Get the client object from current request."""
        token_string = self.get_token_string(request)
        # Ignore empty or JWT format token
        if not token_string or validate_jwt_token(token_string):
            return None
        try:
            token_obj = ClientPrivateToken.objects.get(token=token_string)
        except ClientPrivateToken.DoesNotExist:
            logger.warning(f"private token {token_string} does not exist in database")
            return None

        if token_obj.has_expired():
            logger.warning(f"private token {token_string} has expired")
            return None

        logger.debug(f"private token {token_string} is valid, client_id is {token_obj.client_id}")
        return token_obj.client

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


class AuthenticatedAppAsClientMiddleware:
    """When an API request forwarded by API Gateway was received, if it includes an authenticated
    app(aka "OAuth client") , this middleware will try to attach an system client object to the
    current request according to the app info.

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
        if getattr(request, "sysapi_client", None):
            return

        if client := self.get_client(request, view_func):
            logger.info(
                "Authenticated sysapi client by AuthenticatedApp, name: %s, ip: %s, path: %s",
                client.name,
                get_client_ip(request),
                request.path_info,
            )
            set_sysapi_client(request, client)
        return

    def get_client(self, request, view_func: Callable) -> SysAPIClient | None:
        """Get an sysapi client from current request, if no relation can be found by current
        application, a new client and relation might be created if the view object has been marked
        as "force-allow" by `ForceAllowAuthedApp.mark_view_set`.

        :param request: Current request object.
        :param view_func: Current view function.
        :return: An SysAPIClient object.
        """
        if not getattr(request, "app", None):
            return None
        if not request.app.verified:
            return None

        try:
            obj = AuthenticatedAppAsClient.objects.get(bk_app_code=request.app.bk_app_code, is_active=True)
        except AuthenticatedAppAsClient.DoesNotExist:
            if hasattr(view_func, "cls") and ForceAllowAuthedApp.check_marked(view_func.cls):
                # Automatically create a new user and relation
                return self.create_client(request.app.bk_app_code)
            return None
        else:
            return obj.client

    @staticmethod
    def create_client(bk_app_code: str) -> SysAPIClient:
        """Create a client and relationship from an application code with default permissions."""
        # Create the client
        client, _ = SysAPIClient.objects.get_or_create(
            name=f"authed-app-{bk_app_code}", defaults={"role": ClientRole.BASIC_READER.value}
        )

        # Create the relationship
        AuthenticatedAppAsClient.objects.update_or_create(
            bk_app_code=bk_app_code, defaults={"client": client, "is_active": True}
        )
        return client


def set_sysapi_client(request: HttpRequest, client: SysAPIClient, set_non_cookies: bool = True):
    """Mark current request authenticated with a user stored in database

    :param user: a `models.User` object
    :param set_non_cookies: whether set a special attribute to mark current request was NOT authenticated
        via user cookies.
    """
    request.sysapi_client = client
    if set_non_cookies:
        # Reference from bkpaas_auth
        # Set a special attribute on request to mark this user was not authenticated from
        # cookie, so we may apply other logics afterwards, such as skipping CSRF checks.
        setattr(request, "_bkpaas_auth_authenticated_from_non_cookies", True)
