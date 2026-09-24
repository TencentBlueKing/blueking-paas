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

"""Reading a user's BlueKing login off their request."""

from typing import TYPE_CHECKING

from django.conf import settings

from app_spark_api.infras.accounts.auth import authenticated_user
from app_spark_api.infras.bk_access_token import UserCredential, UserCredentialType

if TYPE_CHECKING:
    from django.http import HttpRequest

# Where a proxy that has already stripped the cookie puts the same value, keyed like
# request.META. Matches the fallback blueking-paas apiserver reads.
_CREDENTIAL_HEADERS = {
    UserCredentialType.BK_TOKEN: "HTTP_X_USER_BK_TOKEN",
    UserCredentialType.BK_TICKET: "HTTP_X_USER_BK_TICKET",
}


def get_user_credential(request: HttpRequest) -> UserCredential | None:
    """Return the caller's BlueKing login, or None when the request does not carry one.

    :param request: Request handled by an operation guarded with login_required.
    :return: The login, tagged with the kind BKAUTH_BACKEND_TYPE says this site uses.
    """
    credential_type = (
        UserCredentialType.BK_TOKEN if settings.BKAUTH_BACKEND_TYPE == "bk_token" else UserCredentialType.BK_TICKET
    )

    # 先 cookie 后请求头，与 apiserver 的 get_user_credential_from_request 同序。
    value = request.COOKIES.get(credential_type.value) or request.META.get(_CREDENTIAL_HEADERS[credential_type])

    # 网关换票要带用户名（rtx），缺了它这份登录态换不出 token，与没有登录态同等处理。
    username = authenticated_user(request).username
    if not value or not username:
        return None
    return UserCredential(type=credential_type, value=value, username=username)
