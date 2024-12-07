# -*- coding: utf-8 -*-
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

from typing import Optional

from bkpaas_auth.core.token import LoginToken
from bkpaas_auth.models import User
from django.conf import settings

from paasng.core.tenant.user import OP_TYPE_TENANT_ID, set_tenant

from .basic import generate_random_string


def create_op_tenant_user(username: Optional[str] = None) -> User:
    """Create an user which belongs to an operation tenant."""
    return create_user(username=username, tenant_id=OP_TYPE_TENANT_ID)


def create_user(username: Optional[str] = None, tenant_id: str | None = None) -> User:
    """Create a user.

    :param username: The user's username, use random value when not given.
    :param tenant_id: The user's tenant id, use a random tenant id when not given.
    """
    username = username or generate_random_string(length=6)
    token = LoginToken(login_token="any_token", expires_in=86400)
    u = User(token=token, provider_type=settings.USER_TYPE, username=username)
    set_tenant(u, tenant_id or generate_random_string(length=6))
    return u
