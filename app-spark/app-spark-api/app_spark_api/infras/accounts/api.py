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

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from django.conf import settings
from ninja import Router, Status

from app_spark_api.infras.accounts.entities import (
    AnonymousUserResponse,
    AuthenticatedUserResponse,
)

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router(tags=["accounts"])


@router.get(
    "/userinfo/",
    response={200: AuthenticatedUserResponse, 401: AnonymousUserResponse},
    url_name="accounts-userinfo",
    summary="获取当前登录的用户信息",
)
async def get_user_info(request: HttpRequest):
    """获取当前已登录的用户信息，如未登录将返回 401 错误。"""
    user = await request.auser()
    if not user.is_authenticated:
        return Status(
            HTTPStatus.UNAUTHORIZED,
            {
                "authenticated": False,
                "login_url": settings.LOGIN_FULL,
            },
        )

    return Status(
        HTTPStatus.OK,
        {
            "authenticated": True,
            "username": user.username,
            "display_name": user.display_name,
            "tenant_id": user.tenant_id,
        },
    )
