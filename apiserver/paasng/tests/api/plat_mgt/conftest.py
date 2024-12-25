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

import pytest
from rest_framework.test import APIClient

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import UserProfile
from tests.utils.auth import create_op_tenant_user, create_user

# TODO 评估是否与 bk_user, api_client 合并（需要做多租户兼容）


@pytest.fixture
def plat_manager_user():
    """平台管理员用户"""
    user = create_op_tenant_user()
    UserProfile.objects.create(user=user.pk, role=SiteRole.ADMIN.value)
    return user


@pytest.fixture
def plat_mgt_api_client(request, plat_manager_user):
    """以平台管理员身份，调用 API"""
    client = APIClient()
    client.force_authenticate(user=plat_manager_user)
    return client


@pytest.fixture
def tenant_manager_user():
    """租户管理员用户"""
    # FIXME（多租户）实现该 fixture，需要兼容租户管理员权限逻辑
    return create_user()


@pytest.fixture
def tenant_mgt_api_client(request, tenant_manager_user):
    """以租户管理员身份，调用 API"""
    client = APIClient()
    client.force_authenticate(user=tenant_manager_user)
    return client
