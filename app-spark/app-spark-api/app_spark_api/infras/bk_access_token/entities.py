# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""The app identity and user login an access_token is exchanged with."""

from enum import StrEnum

import attrs

from app_spark_api.utils import validate_non_empty_string


class UserCredentialType(StrEnum):
    """Which BlueKing login cookie proves who the user is.

    Follows BKAUTH_BACKEND_TYPE: bk_token for the SSM login, bk_ticket otherwise.
    """

    BK_TOKEN = "bk_token"
    BK_TICKET = "bk_ticket"


@attrs.frozen
class UserCredential:
    """A logged-in user's BlueKing login, as read off their request.

    :param type: Which login cookie ``value`` came from.
    :param value: The cookie value; never logged.
    :param username: The user it belongs to.
    """

    type: UserCredentialType
    value: str = attrs.field(repr=False, validator=validate_non_empty_string)
    username: str = attrs.field(validator=validate_non_empty_string)


@attrs.frozen
class AccessTokenClientConfig:
    """How to ask the token service for a user-scoped access_token on behalf of one app.

    :param token_url: The token service's issue endpoint.
    :param app_code: App the token is bound to.
    :param app_secret: That app's secret; never logged, never handed to an Agent Runtime.
    :param env_name: Environment the token is issued for.
    :param timeout_seconds: HTTP timeout for the exchange.
    """

    token_url: str = attrs.field(validator=validate_non_empty_string)
    app_code: str = attrs.field(validator=validate_non_empty_string)
    app_secret: str = attrs.field(repr=False, validator=validate_non_empty_string)
    env_name: str = attrs.field(default="prod", validator=validate_non_empty_string)
    timeout_seconds: float = attrs.field(default=120.0, validator=attrs.validators.gt(0))
