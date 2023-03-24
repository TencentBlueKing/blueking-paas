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
import logging

from bkpaas_auth.models import DatabaseUser
from blue_krill.auth.client import check_client_role

from paasng.accounts.constants import SiteRole
from paasng.accounts.middlewares import set_database_user
from paasng.accounts.models import User, UserProfile

logger = logging.getLogger(__name__)

# 目前已知的 role（jwt client）使用情况：
#
#   - "default"：默认值，暂无特殊用途
#   - "internal-sys"：apiserver 与 workloads 等服务互调系统级 API 时使用
#   - "internal_platform"：调用 PaaS 增强服务的系统级 API 时使用


class SysUserFromVerifiedClientMiddleware:
    """When current request was issued by a verified internal service(using JWT),
    treat current user as an internal system user."""

    _client_role = 'internal-sys'
    _default_username = 'sys-internal-svc-admin'
    _default_role = SiteRole.SYSTEM_API_BASIC_MAINTAINER.value

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ignore already authenticated requests
        if getattr(request, 'user', None) and request.user.is_authenticated:
            return self.get_response(request)

        # Ignore not authenticated clients
        if not check_client_role(request, self._client_role):
            return self.get_response(request)

        set_database_user(request, self.get_default_user())
        return self.get_response(request)

    def get_default_user(self) -> DatabaseUser:
        """Get or create the default admin user from database"""
        user_db, created = User.objects.get_or_create(username=self._default_username)
        user = DatabaseUser.from_db_obj(user_db)
        if created:
            UserProfile.objects.update_or_create(user=user.pk, defaults={'role': self._default_role})
        return user
