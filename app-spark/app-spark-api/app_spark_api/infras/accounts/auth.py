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

"""Authentication for django-ninja operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from bkpaas_auth.models import User
    from django.http import HttpRequest


async def login_required(request: HttpRequest) -> Any | None:
    """Reject anonymous callers, and hand the operation the user it may act for.

    ``ninja.django_auth`` cannot be used from an async operation: it reads ``request.user``,
    whose lazy load is a synchronous database query and raises ``SynchronousOnlyOperation``
    inside an event loop. ``request.auser()`` is the awaitable equivalent.

    :param request: Request being authenticated.
    :return: The authenticated user, or ``None`` to make django-ninja answer 401.
    """
    user = await request.auser()
    return user if user.is_authenticated else None


def authenticated_user(request: HttpRequest) -> User:
    """Return the user :func:`login_required` attached to the request.

    django-ninja stores whatever the auth callable returned on ``request.auth``, which Django's
    own ``HttpRequest`` knows nothing about. Naming that one untyped access here keeps it out of
    every operation that needs the caller's identity.

    :param request: Request handled by an operation guarded with :func:`login_required`.
    :return: The authenticated user.
    """
    return cast("User", request.auth)  # type: ignore[attr-defined]
