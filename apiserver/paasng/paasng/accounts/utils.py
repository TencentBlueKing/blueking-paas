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
from bkpaas_auth import get_user_by_user_id


def get_user_avatar(username):
    """获取用户头像"""
    try:
        from .utils_ext import get_user_avatar_ext

        return get_user_avatar_ext(username)
    except ImportError:
        return ''


def id_to_username(user_id: str) -> str:
    """Get username by decoding user id"""
    return get_user_by_user_id(user_id, username_only=True).username
