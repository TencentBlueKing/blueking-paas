# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from dataclasses import dataclass
from typing import Dict

from typing_extensions import Protocol

from paasng.ci.constants import CIBackend
from paasng.utils.basic import get_username_by_bkpaas_user_id


@dataclass
class BkUserOAuth:
    operator: str
    oauth_token: str = ''

    @classmethod
    def from_request(cls, request) -> 'BkUserOAuth':
        """通过 request 获取 BkUserOAuth 对象，包含 oauth_token"""
        return cls.from_simple_username(request.user.username)

    @classmethod
    def from_user_profile(cls, user: str) -> 'BkUserOAuth':
        """传入 UserProfile.user 字段内容，转换成 username"""
        return cls.from_simple_username(get_username_by_bkpaas_user_id(user))

    @classmethod
    def from_simple_username(cls, username) -> 'BkUserOAuth':
        """通过 username 获取 BkUserOAuth 对象，不包含 oauth_token"""
        return cls(operator=username)

    def to_dict(self) -> Dict:
        return dict(operator=self.operator, oauth_token=self.oauth_token)


@dataclass
class AtomData:
    name: str
    id: str


class CIManager(Protocol):
    backend: CIBackend
