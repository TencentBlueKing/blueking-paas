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
from typing import Optional, Tuple

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.core.token import LoginToken
from bkpaas_auth.models import User
from blue_krill.auth.client import check_client_role
from django.http import HttpRequest
from rest_framework.authentication import BaseAuthentication

logger = logging.getLogger(__name__)


# How long until the faked LoginToken objects were considered expired, in seconds
FAKE_TOKEN_EXPIRES_IN = 86400


class UserFromVerifiedClientAuthentication(BaseAuthentication):
    """Consider user provided by verified client as current user"""

    valid_jwt_role = 'service-proxy'

    def authenticate(self, request: HttpRequest) -> Optional[Tuple[User, None]]:
        if not check_client_role(request, self.valid_jwt_role):
            # Return `None` to indicate that current authenticator fail to succeed, this follows the protocol
            # of DRF's authenticator, see: https://www.django-rest-framework.org/api-guide/authentication/
            return None

        user_pk = request.extra_payload.get('current_user_pk')
        if user_pk:
            user = get_user_by_user_id(user_pk, username_only=True)
            # Set an un-expired token to make user "authenticated", otherwise it will be treated
            # as un-authenticated.
            user.token = LoginToken(login_token='any_token', expires_in=FAKE_TOKEN_EXPIRES_IN)
            return user, None
        return None
