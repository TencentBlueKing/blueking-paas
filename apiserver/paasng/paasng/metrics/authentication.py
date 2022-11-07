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
import secrets

from django.conf import settings
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed


class BasicAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        username = request.GET.get('client_id', '')
        password = request.GET.get('user_token', '')

        if not (username and password):
            raise AuthenticationFailed('authentication failed: no valid client_id/user_token provided')

        if not secrets.compare_digest(password, settings.METRIC_CLIENT_TOKEN_DICT.get(username, '')):
            raise AuthenticationFailed('authentication failed: incorrect client_id or user_token')

        return ({'username': username, 'password': password}, None)
