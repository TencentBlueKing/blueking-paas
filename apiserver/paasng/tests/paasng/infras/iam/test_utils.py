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
from django.core.management import call_command

from paasng.infras.iam.permissions.resources.application import AppRole
from paasng.infras.iam.utils import get_app_actions_by_role, get_paas_authorization_scopes
from paasng.platform.applications.constants import ApplicationRole


class TestGetAppActionsByRole:
    @pytest.mark.parametrize(
        ("role", "expected"),
        [
            (ApplicationRole.ADMINISTRATOR, AppRole.get_actions(AppRole.ADMINISTRATOR)),
            (ApplicationRole.DEVELOPER, AppRole.get_actions(AppRole.DEVELOPER)),
            (ApplicationRole.OPERATOR, AppRole.get_actions(AppRole.OPERATOR)),
            (ApplicationRole.ADMINISTRATOR.value, AppRole.get_actions(AppRole.ADMINISTRATOR)),
            (ApplicationRole.DEVELOPER.value, AppRole.get_actions(AppRole.DEVELOPER)),
            (ApplicationRole.OPERATOR.value, AppRole.get_actions(AppRole.OPERATOR)),
        ],
    )
    def test_accepts_enum_and_raw_int(self, role, expected):
        assert get_app_actions_by_role(role) == list(expected)

    @pytest.mark.parametrize("role", [ApplicationRole.NOBODY, ApplicationRole.COLLABORATOR, -1, 1])
    def test_roles_without_iam_mapping_return_empty(self, role):
        assert get_app_actions_by_role(role) == []

    def test_unknown_int_raises(self):
        with pytest.raises(ValueError, match="99"):
            get_app_actions_by_role(99)


class TestGetPaasAuthorizationScopes:
    def test_raw_int_role_keeps_developer_actions(self, settings):
        settings.IAM_PAAS_V3_SYSTEM_ID = "bk_paas3"

        scopes = get_paas_authorization_scopes("demo", "Demo", ApplicationRole.DEVELOPER.value)

        assert {item["id"] for item in scopes["actions"]} == set(AppRole.get_actions(AppRole.DEVELOPER))


class RecordingIAMClient:
    """记录回收 / 重授顺序，重授时走真实的 scopes 计算"""

    instances: list = []

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.calls: list = []
        self.__class__.instances.append(self)

    def revoke_user_group_policies(self, user_group_id, actions):
        self.calls.append(("revoke", user_group_id, list(actions)))

    def grant_user_group_policies(self, app_code, app_name, groups):
        scopes = get_paas_authorization_scopes(app_code, app_name, groups[0]["role"])
        self.calls.append(("grant", groups, scopes))


class TestRegrantUserGroupPolicies:
    def test_revoke_then_regrant_with_raw_int_role(self, settings):
        """库里的 role 是裸 int。先回收再授权时，不能因 AttributeError 只回收不重授。"""
        settings.IAM_PAAS_V3_SYSTEM_ID = "bk_paas3"
        group = mock.Mock(app_code="demo", user_group_id=1001, role=ApplicationRole.DEVELOPER.value)
        assert type(group.role) is int

        apps_qs = mock.Mock()
        apps_qs.values_list.return_value = [("demo", "Demo")]
        groups_qs = mock.Mock()
        groups_qs.count.return_value = 1
        groups_qs.__iter__ = mock.Mock(return_value=iter([group]))

        RecordingIAMClient.instances = []
        command_mod = "paasng.infras.iam.members.management.commands.regrant_user_group_policies"
        with (
            mock.patch(f"{command_mod}.Application.objects.filter", return_value=apps_qs),
            mock.patch(f"{command_mod}.ApplicationUserGroup.objects.filter", return_value=groups_qs),
            mock.patch(f"{command_mod}.get_tenant_id_for_app", return_value="default"),
            mock.patch(f"{command_mod}.BKIAMClient", new=RecordingIAMClient),
        ):
            call_command("regrant_user_group_policies", "--codes", "demo", "--role", "developer")

        assert len(RecordingIAMClient.instances) == 1
        calls = RecordingIAMClient.instances[0].calls
        assert [item[0] for item in calls] == ["revoke", "grant"]
        assert calls[0][1] == 1001
        grant_groups, grant_scopes = calls[1][1], calls[1][2]
        assert grant_groups == [{"id": 1001, "role": ApplicationRole.DEVELOPER.value}]
        assert {item["id"] for item in grant_scopes["actions"]} == set(AppRole.get_actions(AppRole.DEVELOPER))
