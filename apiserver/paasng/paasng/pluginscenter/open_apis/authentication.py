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
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed

from paasng.pluginscenter.itsm_adaptor.client import ItsmClient


class ItsmBasicAuthentication(BasicAuthentication):
    """自定义认证逻辑，对 ITSM 请求认证"""

    def authenticate(self, request):
        """
        验证回调请求是否来自 ITSM
        https://github.com/TencentBlueKing/bk-itsm/blob/master/docs/wiki/access.md
        """
        login_cookie = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
        token = request.data.get('token', '')

        client = ItsmClient(login_cookie=login_cookie)
        is_passed = client.verify_token(token)
        if not is_passed:
            raise AuthenticationFailed('authentication failed: itsm callback token verification failed')

        return is_passed
