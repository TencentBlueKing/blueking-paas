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

"""测试工具函数。"""

import random
from typing import Optional

from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.token import LoginToken
from bkpaas_auth.models import User

DFT_RANDOM_CHARACTER_SET = "abcdefghijklmnopqrstuvwxyz" + "0123456789"


def generate_random_string(length: int = 30, chars: str = DFT_RANDOM_CHARACTER_SET) -> str:
    """Generates a non-guessable random string."""
    rand = random.SystemRandom()
    return "".join(rand.choice(chars) for _ in range(length))


def create_user(username: Optional[str] = None, tenant_id: Optional[str] = None) -> User:
    """Create a user.

    :param username: The user's username, use random value when not given.
    :param tenant_id: The user's tenant id, use a random tenant id when not given.
    """
    username = username or generate_random_string(length=6)
    token = LoginToken(login_token="any_token", expires_in=86400)
    user = User(
        token=token,
        provider_type=ProviderType.RTX,
        username=username,
        display_name=username,
    )
    user.tenant_id = tenant_id or generate_random_string(length=6)
    return user
