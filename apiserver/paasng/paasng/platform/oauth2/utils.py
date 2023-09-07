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
from typing import Optional

from django.conf import settings
from django.utils.crypto import get_random_string

from paasng.platform.oauth2.api import BkAppSecret, BkOauthClient
from paasng.platform.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.platform.oauth2.models import BuiltinBkAppSecret, OAuth2Client


def get_random_secret_key():
    """
    Return a 50 character random string usable as a SECRET_KEY setting value.
    """
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return get_random_string(50, chars)


def create_oauth2_client(bk_app_code: str, region: str) -> bool:
    """Create oauth2 client for application"""
    if settings.ENABLE_BK_OAUTH:
        return BkOauthClient().create_client(bk_app_code)

    OAuth2Client.objects.get_or_create(
        region=region, client_id=bk_app_code, defaults={'client_secret': get_random_secret_key()}
    )
    return True


def get_builtin_app_secret_id(bk_app_code: str) -> Optional[int]:
    try:
        return BuiltinBkAppSecret.objects.get(bk_app_code=bk_app_code).bk_app_secret_id
    except BuiltinBkAppSecret.DoesNotExist:
        return None


def get_bulitin_app_secret(bk_app_code: str) -> BkAppSecret:
    client = BkOauthClient()

    # 如果平台 DB 中记录了内置密钥的 ID，则以平台记录的为准
    if bk_app_secret_id := get_builtin_app_secret_id(bk_app_code):
        secret_in_db = client.get_secret_by_id(bk_app_code, str(bk_app_secret_id))
        if secret_in_db:
            return secret_in_db

    # 平台中没有记录，则从 bkAuth 返回的 API 中选择默认的密钥: 已启用且创建时间最早的
    return client.get_default_app_secret(bk_app_code)


def get_oauth2_client_secret(bk_app_code: str, region: str) -> str:
    if settings.ENABLE_BK_OAUTH:
        return get_bulitin_app_secret(bk_app_code).bk_app_secret

    try:
        client_secret = OAuth2Client.objects.get(region=region, client_id=bk_app_code).client_secret
    except OAuth2Client.DoesNotExist:
        raise BkOauthClientDoesNotExist(f"Bk Oauth client({bk_app_code}) not exist")
    return client_secret
