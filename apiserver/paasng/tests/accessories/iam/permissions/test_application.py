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
import pytest
from django.conf import settings

from paasng.accessories.iam.constants import ResourceType
from paasng.accessories.iam.permissions.exceptions import PermissionDeniedError
from paasng.accessories.iam.permissions.perm import ActionResourcesRequest
from paasng.accessories.iam.permissions.resources.application import AppAction, AppCreatorAction, AppPermCtx
from tests.accessories.iam.conftest import generate_apply_url
from tests.utils.helpers import generate_random_string

from . import roles

TEST_APP_CODE = generate_random_string(10)
TEST_APP_NAME = generate_random_string(6)

pytestmark = pytest.mark.django_db


class TestApplicationPermission:
    """测试蓝鲸应用资源权限"""

    def test_can_view_basic_info(self, app_permission_obj):
        """测试场景：有查看基础信息权限（管理，开发，运营都有权限）"""
        perm_ctx = AppPermCtx(username=roles.APP_ADMIN_USER, code=TEST_APP_CODE)
        assert app_permission_obj.can_view_basic_info(perm_ctx)

        perm_ctx.username = roles.APP_DEVELOP_USER
        assert app_permission_obj.can_view_basic_info(perm_ctx)

        perm_ctx.username = roles.APP_OPERATE_USER
        assert app_permission_obj.can_view_basic_info(perm_ctx)

    def test_can_delete_application(self, app_permission_obj):
        """测试场景：删除应用（仅管理有权限）"""
        perm_ctx = AppPermCtx(username=roles.APP_ADMIN_USER, code=TEST_APP_CODE)
        assert app_permission_obj.can_delete_application(perm_ctx)

        perm_ctx.username = roles.APP_OPERATE_USER
        assert not app_permission_obj.can_delete_application(perm_ctx, raise_exception=False)

        # 无权限抛出异常
        with pytest.raises(PermissionDeniedError) as exec:
            app_permission_obj.can_delete_application(perm_ctx)
        assert exec.value.code == PermissionDeniedError.code
        assert exec.value.data['perms']['apply_url'] == generate_apply_url(
            roles.APP_OPERATE_USER,
            action_request_list=[
                ActionResourcesRequest(
                    AppAction.DELETE_APPLICATION,
                    resource_type=ResourceType.Application,
                    resources=[TEST_APP_CODE],
                )
            ],
        )

    def test_can_manage_cloud_api(self, app_permission_obj):
        """测试场景：云 API 管理（仅管理，开发可用）"""
        perm_ctx = AppPermCtx(username=roles.APP_ADMIN_USER, code=TEST_APP_CODE)
        assert app_permission_obj.can_manage_cloud_api(perm_ctx)

        perm_ctx.username = roles.APP_DEVELOP_USER
        assert app_permission_obj.can_manage_cloud_api(perm_ctx)

        perm_ctx.username = roles.APP_OPERATE_USER
        assert not app_permission_obj.can_manage_cloud_api(perm_ctx, raise_exception=False)

    def test_can_manage_app_market(self, app_permission_obj):
        """测试场景：应用市场管理（仅管理，运营可用）"""
        perm_ctx = AppPermCtx(username=roles.APP_ADMIN_USER, code=TEST_APP_CODE)
        assert app_permission_obj.can_manage_app_market(perm_ctx)

        perm_ctx.username = roles.APP_OPERATE_USER
        assert app_permission_obj.can_manage_app_market(perm_ctx)

        perm_ctx.username = roles.APP_DEVELOP_USER
        assert not app_permission_obj.can_manage_app_market(perm_ctx, raise_exception=False)


class TestApplicationCreatorAction:
    def test_to_data(self, bk_user):
        action = AppCreatorAction(bk_user.username, code=TEST_APP_CODE, name=TEST_APP_NAME)
        assert action.to_data() == {
            'id': TEST_APP_CODE,
            'name': TEST_APP_NAME,
            'creator': bk_user.username,
            'type': ResourceType.Application,
            'system': settings.IAM_PAAS_V3_SYSTEM_ID,
        }
