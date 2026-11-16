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

from unittest import mock

import pytest

from paasng.infras.iam.helpers import add_role_members
from paasng.plat_mgt.applications.tasks import remove_temp_admin
from paasng.platform.applications.constants import ApplicationRole

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mock_iam_client():
    from tests.utils.mocks.iam import StubBKIAMClient

    with (
        mock.patch("paasng.infras.iam.v3.management.BKIAMClient", new=StubBKIAMClient),
        mock.patch("paasng.infras.iam.client.BKIAMClient", new=StubBKIAMClient),
    ):
        yield


@pytest.fixture()
def temp_admin(bk_plugin_app):
    """把 temp-admin 设为应用的临时管理员"""
    add_role_members(bk_plugin_app.code, ApplicationRole.ADMINISTRATOR, "temp-admin")
    return "temp-admin"


def test_remove_maintainer_after_task_removes_admin(temp_admin, bk_plugin_app, mocker):
    """主链路: 临时管理员退出后, 任务会携带该用户去清理网关维护人"""
    signal = mocker.patch("paasng.plat_mgt.applications.tasks.application_member_updated")

    remove_temp_admin.apply(args=(bk_plugin_app.code, temp_admin)).get()

    signal.send.assert_called_once_with(
        sender=bk_plugin_app, application=bk_plugin_app, removed_usernames=[temp_admin]
    )
