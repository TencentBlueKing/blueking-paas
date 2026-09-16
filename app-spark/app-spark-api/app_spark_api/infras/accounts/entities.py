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

from typing import Literal

from ninja import Field, Schema


class AnonymousUserResponse(Schema):
    """未登录用户请求用户信息时返回的 401 响应体。"""

    authenticated: Literal[False] = Field(description="是否已登录")
    login_url: str = Field(description="登录页完整 URL")


class AuthenticatedUserResponse(Schema):
    """当前登录用户的用户信息。"""

    authenticated: Literal[True] = Field(description="是否已登录")
    username: str = Field(description="用户登录名")
    display_name: str = Field(description="用户展示名")
    tenant_id: str | None = Field(description="所属租户的 ID")
