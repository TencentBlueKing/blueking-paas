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

from paasng.accessories.iam.permissions.resources.admin42 import Admin42PermCtx

from . import roles

pytestmark = pytest.mark.django_db


class TestAdmin42Permission:
    """测试蓝鲸 PaaS 平台数据权限"""

    def test_can_manage_platform(self, admin42_permission_obj):
        """测试场景：能管理平台基础信息"""
        perm_ctx = Admin42PermCtx(username=roles.PLATFORM_ADMIN_USER)
        assert admin42_permission_obj.can_manage_platform(perm_ctx)

        perm_ctx.username = roles.APP_TMPL_ADMIN_USER
        assert not admin42_permission_obj.can_manage_platform(perm_ctx, raise_exception=False)

        perm_ctx.username = roles.PLATFORM_OPERATE_USER
        assert not admin42_permission_obj.can_manage_platform(perm_ctx, raise_exception=False)

    def test_can_manage_app_templates(self, admin42_permission_obj):
        """测试场景：能管理应用模板"""
        perm_ctx = Admin42PermCtx(username=roles.PLATFORM_ADMIN_USER)
        assert not admin42_permission_obj.can_manage_app_templates(perm_ctx, raise_exception=False)

        perm_ctx.username = roles.APP_TMPL_ADMIN_USER
        assert admin42_permission_obj.can_manage_app_templates(perm_ctx)

        perm_ctx.username = roles.PLATFORM_OPERATE_USER
        assert not admin42_permission_obj.can_manage_app_templates(perm_ctx, raise_exception=False)

    def test_can_operate_platform(self, admin42_permission_obj):
        """测试场景：能查看平台运营数据"""
        perm_ctx = Admin42PermCtx(username=roles.PLATFORM_ADMIN_USER)
        assert not admin42_permission_obj.can_operate_platform(perm_ctx, raise_exception=False)

        perm_ctx.username = roles.APP_TMPL_ADMIN_USER
        assert not admin42_permission_obj.can_operate_platform(perm_ctx, raise_exception=False)

        perm_ctx.username = roles.PLATFORM_OPERATE_USER
        assert admin42_permission_obj.can_operate_platform(perm_ctx)
