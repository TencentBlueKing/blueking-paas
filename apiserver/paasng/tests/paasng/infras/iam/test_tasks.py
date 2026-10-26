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

from paasng.infras.iam.constants import APP_DEFAULT_ROLES
from paasng.infras.iam.members.models import ApplicationGradeManager, ApplicationUserGroup
from paasng.infras.iam.tasks import add_monitoring_space_permission

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_add_monitoring_space_permission(bk_app):
    ApplicationGradeManager.objects.update_or_create(app_code=bk_app.code, defaults={"grade_manager_id": 42})
    for group_id, role in enumerate(APP_DEFAULT_ROLES, start=11):
        ApplicationUserGroup.objects.update_or_create(
            app_code=bk_app.code, role=role, defaults={"user_group_id": group_id}
        )

    backend = mock.Mock()
    with mock.patch("paasng.infras.iam.tasks.get_management_backend", return_value=backend):
        add_monitoring_space_permission(bk_app.code, bk_app.name, "-100")

    backend.update_management_space_scopes.assert_called_once_with(42, bk_app.code, bk_app.name, "-100")
    for method in [backend.grant_user_group_policies_in_bk_monitor, backend.grant_user_group_policies_in_bk_log]:
        bk_space_id, app_name, groups = method.call_args.args
        assert (bk_space_id, app_name) == ("-100", bk_app.name)
        assert [(group.id, group.role) for group in groups] == [
            (11 + idx, int(role)) for idx, role in enumerate(APP_DEFAULT_ROLES)
        ]
    # 必须先扩大管理空间的权限范围，用户组才能被授予监控、日志权限
    assert [call[0] for call in backend.method_calls] == [
        "update_management_space_scopes",
        "grant_user_group_policies_in_bk_monitor",
        "grant_user_group_policies_in_bk_log",
    ]
