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

from django.utils.crypto import get_random_string

from paasng.infras.oauth2.api import BkAppSecret, BkOauthClient
from paasng.infras.oauth2.models import BkAppSecretInEnvVar


def get_random_secret_key():
    """
    Return a 50 character random string usable as a SECRET_KEY setting value.
    """
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return get_random_string(50, chars)


def create_oauth2_client(bk_app_code: str, app_tenant_mode: str, app_tenant_id: str) -> bool:
    """Create oauth2 client for application"""
    return BkOauthClient().create_client(bk_app_code, app_tenant_mode, app_tenant_id)


def get_app_secret_in_env_var(bk_app_code: str) -> BkAppSecret:
    """应用部署时，写入环境变量中的密钥
    如果用户未主动设置，则为 BkAuth API 中返回的默认密钥
    """
    client = BkOauthClient()

    # 如果平台 DB 中记录了环境变量默认密钥的 ID，则以平台记录的为准
    try:
        secret_in_db = BkAppSecretInEnvVar.objects.get(bk_app_code=bk_app_code).bk_app_secret_id
    except BkAppSecretInEnvVar.DoesNotExist:
        secret_in_db = None
    if secret_in_db:
        secret_in_db = client.get_secret_by_id(bk_app_code, secret_in_db)
        if secret_in_db:
            return secret_in_db
    # 平台中没有记录，则从 bkAuth 返回的 API 中选择默认的密钥: 已启用且创建时间最早的
    return client.get_default_app_secret(bk_app_code)


def get_oauth2_client_secret(bk_app_code: str) -> str:
    """获取应用的 OAuth 默认密钥"""
    return get_app_secret_in_env_var(bk_app_code).bk_app_secret
