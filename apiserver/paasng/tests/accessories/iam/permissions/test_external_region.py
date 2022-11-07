# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
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
import pytest

from paasng.accessories.iam.permissions.resources.external_region import ExternalRegionPermCtx

from . import roles

pytestmark = pytest.mark.django_db


class TestExternalRegionPermission:
    """测试蓝鲸外部版应用权限"""

    def test_can_create_external_region_app(self, external_region_permission_obj):
        """测试场景：有创建外部版应用权限"""
        perm_ctx = ExternalRegionPermCtx(username=roles.EXTERNAL_REGION_ENABLED_USER)
        assert external_region_permission_obj.can_create_external_region_app(perm_ctx)

        perm_ctx.username = roles.APP_DEVELOP_USER
        assert not external_region_permission_obj.can_create_external_region_app(perm_ctx, raise_exception=False)

    def test_can_create_external_region_module(self, external_region_permission_obj):
        """测试场景：有创建外部版模块权限"""
        perm_ctx = ExternalRegionPermCtx(username=roles.EXTERNAL_REGION_ENABLED_USER)
        assert external_region_permission_obj.can_create_external_region_module(perm_ctx)

        perm_ctx.username = roles.APP_ADMIN_USER
        assert not external_region_permission_obj.can_create_external_region_module(perm_ctx, raise_exception=False)
