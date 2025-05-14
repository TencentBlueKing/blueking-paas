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

from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import PrivateTokenHolder, User, UserProfile


def ensure_builtin_user():
    """初始化内置的操作用户。内置用户的主要功能，是用来持有访问部分源码管理系统的 private token。"""
    conf = settings.PLUGIN_REPO_CONF
    username = conf["username"]

    # 创建平台系统用户
    User.objects.get_or_create(username=username)
    user_id = user_id_encoder.encode(ProviderType.DATABASE, username)
    # This user only acts as a holder for the sourcectl private token, so no specific
    # role is required.
    profile, _ = UserProfile.objects.update_or_create(user=user_id, defaults={"role": SiteRole.USER.value})
    profile.refresh_from_db(fields=["role"])

    # 关联源码管理的 private_token
    PrivateTokenHolder.objects.update_or_create(
        user=profile,
        provider="tc_git",
        defaults={
            "private_token": conf["private_token"],
            "expire_at": None,
        },
    )
