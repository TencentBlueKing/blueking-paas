# -*- coding: utf-8 -*-
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

from typing import TYPE_CHECKING

from bkpaas_auth import get_user_by_user_id
from django.conf import settings
from django.db import models

from app_spark_api.core.tenant.fields import tenant_id_field_factory
from app_spark_api.core.tenant.user import get_tenant
from app_spark_api.infras.accounts.constants import SiteRole
from app_spark_api.utils.models import BkUserField, TimestampedModel

if TYPE_CHECKING:
    from bkpaas_auth.models import User as RequestUser


class UserProfileManager(models.Manager):
    """Custom profile manager for user"""

    def get_profile(self, user: "RequestUser"):
        """获取或创建用户基本信息，包含用户权限、特性等。

        :param user: 通过 request.user 获取的用户信息
        """
        if user.pk is None or not user.pk:
            raise ValueError("Must provide a real user, not an anonymous user!")

        current_tenant_id = get_tenant(user).id

        # 用户首次访问时，自动创建普通用户。否则必须手动将用户添加到 UserProfile 表后，才能访问站点。
        if settings.AUTO_CREATE_REGULAR_USER:
            profile, _ = self.get_or_create(
                user=user.pk,
                defaults={"tenant_id": current_tenant_id, "role": SiteRole.USER.value},
            )
            return profile

        return self.get(user=user.pk)

    def get_by_natural_key(self, user: str):
        return self.get(user=user)


class UserProfile(TimestampedModel):
    """Profile field for user"""

    user = BkUserField(unique=True)
    role = models.IntegerField(default=SiteRole.USER.value)
    feature_flags = models.TextField(null=True, blank=True)

    tenant_id = tenant_id_field_factory()

    objects = UserProfileManager()

    @property
    def username(self):
        if self.user is None:
            raise ValueError("UserProfile.user must not be None")
        return get_user_by_user_id(self.user, username_only=True).username

    def __str__(self):
        return "{user}-{role}".format(user=self.username, role=self.role)

    def natural_key(self):
        return (self.user,)
