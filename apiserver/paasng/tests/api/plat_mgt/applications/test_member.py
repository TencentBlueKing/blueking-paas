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


from unittest import mock

import pytest
from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.urls import reverse

from paasng.infras.iam.members.models import ApplicationUserGroup
from paasng.platform.applications.models import ApplicationMembership
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mock_iam_client():
    from tests.utils.mocks.iam import StubBKIAMClient

    with (
        mock.patch("paasng.infras.iam.helpers.BKIAMClient", new=StubBKIAMClient),
        mock.patch("paasng.infras.iam.client.BKIAMClient", new=StubBKIAMClient),
    ):
        yield


class TestApplicationMemberViewSet:
    def _assert_user_in_role(self, app, role, username, should_exist=True) -> bool:
        """辅助方法：判断用户是否存在于特定角色中"""
        members = ApplicationMembership.objects.filter(application=app, role=role)
        user_found = False
        for member in members:
            user_id = member.user
            user_object = get_user_by_user_id(user_id)

            if user_object and user_object.username == username:
                user_found = True
                break

        if should_exist:
            return user_found
        else:
            return not user_found

    def test_list(self, plat_mgt_api_client, bk_app):
        url = reverse("plat_mgt.applications.members", kwargs={"app_code": bk_app.code})
        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert len(rsp.data) > 0

    def test_create(self, plat_mgt_api_client, bk_app):
        url = reverse("plat_mgt.applications.members", kwargs={"app_code": bk_app.code})
        data = [{"user": {"username": "test_user"}, "roles": [{"id": 2}]}]
        rsp = plat_mgt_api_client.post(url, data=data)
        assert rsp.status_code == 201

        # 检查数据库是否有对应的用户组和成员
        assert ApplicationUserGroup.objects.filter(app_code=bk_app.code, role=2).exists()
        assert self._assert_user_in_role(bk_app, 2, "test_user")

    def test_become_temp_admin(self, plat_mgt_api_client, bk_app):
        url = reverse("plat_mgt.applications.members.temp_admin", kwargs={"app_code": bk_app.code})
        username = plat_mgt_api_client.handler._force_user.username
        with mock.patch("paasng.plat_mgt.applications.views.member.remove_temp_admin.apply_async") as mock_apply_async:
            rsp = plat_mgt_api_client.post(url)
            assert rsp.status_code == 204

            # 检查数据库是否有对应的用户组和成员
            assert ApplicationUserGroup.objects.filter(app_code=bk_app.code, role=2).exists()
            assert self._assert_user_in_role(bk_app, 2, username)

            mock_apply_async.assert_called_once_with(
                args=[bk_app.code, username],
                countdown=2 * 60 * 60,
            )

    def test_update(self, plat_mgt_api_client, bk_app):
        # 准备测试数据
        test_user = create_user()
        ApplicationUserGroup.objects.get_or_create(
            app_code=bk_app.code, role=2, defaults={"name": "Developer user group", "readonly": True}
        )
        ApplicationMembership.objects.create(application=bk_app, role=2, user=test_user)

        assert self._assert_user_in_role(bk_app, 2, test_user.username)

        # 执行更新操作
        user_id = user_id_encoder.encode(username=test_user.username, provider_type=settings.USER_TYPE)
        url = reverse("plat_mgt.applications.members.detail", kwargs={"app_code": bk_app.code, "user_id": user_id})
        data = {"role": {"id": 3}}
        rsp = plat_mgt_api_client.put(url, data=data)
        assert rsp.status_code == 204

        # 检查成员已经更换角色
        assert ApplicationUserGroup.objects.filter(app_code=bk_app.code, role=3).exists()
        assert self._assert_user_in_role(bk_app, 3, test_user.username)

    def test_destroy(self, plat_mgt_api_client, bk_app):
        # 准备测试数据
        test_user = create_user()
        ApplicationUserGroup.objects.get_or_create(
            app_code=bk_app.code, role=2, defaults={"name": "Developer user group", "readonly": True}
        )
        ApplicationMembership.objects.create(application=bk_app, role=2, user=test_user)
        ## 确认成员已创建

        assert self._assert_user_in_role(bk_app, 2, test_user.username)

        # 执行删除操作
        user_id = user_id_encoder.encode(username=test_user.username, provider_type=settings.USER_TYPE)
        url = reverse("plat_mgt.applications.members.detail", kwargs={"app_code": bk_app.code, "user_id": user_id})
        rsp = plat_mgt_api_client.delete(url)
        assert rsp.status_code == 204

        # 检查成员已被删除
        assert self._assert_user_in_role(bk_app, 2, test_user.username, should_exist=False)

    def test_get_roles(self, plat_mgt_api_client):
        url = reverse("plat_mgt.applications.members.get_roles")
        rsp = plat_mgt_api_client.get(url)
        assert rsp.status_code == 200
        assert "results" in rsp.data
