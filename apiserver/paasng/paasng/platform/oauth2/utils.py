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
from django.conf import settings
from django.utils.crypto import get_random_string

from paasng.platform.oauth2.api import BkOauthClient
from paasng.platform.oauth2.exceptions import BkOauthClientDoesNotExist
from paasng.platform.oauth2.models import OAuth2Client


def get_random_secret_key():
    """
    Return a 50 character random string usable as a SECRET_KEY setting value.
    """
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return get_random_string(50, chars)


def create_oauth2_client(code: str, region: str) -> bool:
    """Create oauth2 client for application"""
    if settings.ENABLE_BK_OAUTH:
        return BkOauthClient().create_client(code)

    OAuth2Client.objects.get_or_create(
        region=region, client_id=code, defaults={'client_secret': get_random_secret_key()}
    )
    return True


def get_oauth2_client_secret(code: str, region: str) -> str:
    if settings.ENABLE_BK_OAUTH:
        return BkOauthClient().get_client_secret(code)

    try:
        client_secret = OAuth2Client.objects.get(region=region, client_id=code).client_secret
    except OAuth2Client.DoesNotExist:
        raise BkOauthClientDoesNotExist(f"Bk Oauth client({code}) not exist")
    return client_secret
