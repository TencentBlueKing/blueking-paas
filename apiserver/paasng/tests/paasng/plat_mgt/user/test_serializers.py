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
from django.test import override_settings

from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.plat_mgt.users.serializers import CreatePlatformManagerSLZ

pytestmark = pytest.mark.django_db


class TestCreatePlatformManagerSLZ:
    @override_settings(ENABLE_MULTI_TENANT_MODE=False)
    def test_create_platform_manager_slz_without_tenant_id(self):
        """测试在多租户模式未启用时，租户 ID 的默认值"""
        data = {"user": "testuser"}
        slz = CreatePlatformManagerSLZ(data=data)
        assert slz.is_valid(), slz.errors
        assert slz.validated_data["tenant_id"] == DEFAULT_TENANT_ID

        # 即使传了 tenant_id，也会被覆盖为默认值
        data = {"user": "testuser", "tenant_id": "custom"}
        slz = CreatePlatformManagerSLZ(data=data)
        assert slz.is_valid(), slz.errors
        assert slz.validated_data["tenant_id"] == DEFAULT_TENANT_ID

    @override_settings(ENABLE_MULTI_TENANT_MODE=True)
    def test_create_platform_manager_slz_with_tenant_id(self):
        """测试在多租户模式启用时，租户 ID 的验证"""
        data = {"user": "testuser", "tenant_id": "custom"}
        slz = CreatePlatformManagerSLZ(data=data)
        assert slz.is_valid(), slz.errors
        assert slz.validated_data["tenant_id"] == "custom"

        # 如果没有 tenant_id，则验证失败
        data = {"user": "testuser"}
        slz = CreatePlatformManagerSLZ(data=data)
        assert not slz.is_valid()
        assert "tenant_id" in slz.errors
