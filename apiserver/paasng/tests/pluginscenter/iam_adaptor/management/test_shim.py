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
from typing import List

import cattr
import pytest
from django_dynamic_fixture import G

from paasng.pluginscenter.constants import PluginRole
from paasng.pluginscenter.iam_adaptor.management import shim
from paasng.pluginscenter.iam_adaptor.models import PluginGradeManager, PluginUserGroup

pytestmark = pytest.mark.django_db


def test_fetch_grade_manager_members(plugin, iam_management_client):
    G(PluginGradeManager, pd_id=plugin.pd.identifier, plugin_id=plugin.id, grade_manager_id=1)
    assert shim.fetch_grade_manager_members(plugin) == ["admin", "test"]
    assert iam_management_client.management_grade_manager_members.called


def test_fetch_role_members(plugin, iam_management_client):
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.ADMINISTRATOR, user_group_id=1)
    assert shim.fetch_role_members(plugin, PluginRole.ADMINISTRATOR) == ["admin"]
    assert iam_management_client.v2_management_group_members.called

    with pytest.raises(PluginUserGroup.DoesNotExist):
        shim.fetch_role_members(plugin, PluginRole.DEVELOPER)

    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.DEVELOPER, user_group_id=2)
    iam_management_client.reset_mock(visited=None)
    assert not iam_management_client.v2_management_group_members.called

    assert shim.fetch_role_members(plugin, PluginRole.DEVELOPER) == ["admin", "foo", "bar"]
    assert iam_management_client.v2_management_group_members.called


def test_add_role_members(plugin, iam_management_client):
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.ADMINISTRATOR, user_group_id=1)
    G(PluginGradeManager, pd_id=plugin.pd.identifier, plugin_id=plugin.id, grade_manager_id=1)
    shim.add_role_members(plugin, PluginRole.ADMINISTRATOR, ["foo"])

    assert iam_management_client.management_add_grade_manager_members.called
    assert iam_management_client.v2_management_add_group_members.called

    with pytest.raises(PluginUserGroup.DoesNotExist):
        shim.add_role_members(plugin, PluginRole.DEVELOPER, ["foo"])

    iam_management_client.reset_mock(visited=None)
    assert not iam_management_client.management_add_grade_manager_members.called
    assert not iam_management_client.v2_management_add_group_members.called

    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.DEVELOPER, user_group_id=2)
    shim.add_role_members(plugin, PluginRole.DEVELOPER, ["foo"])
    assert not iam_management_client.management_add_grade_manager_members.called
    assert iam_management_client.v2_management_add_group_members.called


def test_delete_role_members(plugin, iam_management_client):
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.ADMINISTRATOR, user_group_id=1)
    G(PluginGradeManager, pd_id=plugin.pd.identifier, plugin_id=plugin.id, grade_manager_id=1)
    shim.delete_role_members(plugin, PluginRole.ADMINISTRATOR, ["foo"])

    assert iam_management_client.management_delete_grade_manager_members.called
    assert iam_management_client.v2_management_delete_group_members.called

    with pytest.raises(PluginUserGroup.DoesNotExist):
        shim.delete_role_members(plugin, PluginRole.DEVELOPER, ["foo"])

    iam_management_client.reset_mock(visited=None)
    assert not iam_management_client.management_delete_grade_manager_members.called
    assert not iam_management_client.v2_management_delete_group_members.called

    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.DEVELOPER, user_group_id=2)
    shim.delete_role_members(plugin, PluginRole.DEVELOPER, ["foo"])
    assert not iam_management_client.management_delete_grade_manager_members.called
    assert iam_management_client.v2_management_delete_group_members.called


def test_fetch_user_roles(plugin, iam_management_client):
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.DEVELOPER, user_group_id=2)
    assert shim.fetch_user_roles(plugin, "admin") == [PluginRole.DEVELOPER]

    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.ADMINISTRATOR, user_group_id=1)
    assert shim.fetch_user_roles(plugin, "admin") == [PluginRole.ADMINISTRATOR, PluginRole.DEVELOPER]

    assert iam_management_client.v2_management_group_members.called

    # test user not found(no any role)
    iam_management_client.reset_mock(visited=None)
    assert shim.fetch_user_roles(plugin, "baz") == []
    assert iam_management_client.v2_management_group_members.called


def test_remove_user_all_roles(plugin, iam_management_client):
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.ADMINISTRATOR, user_group_id=1)
    G(PluginGradeManager, pd_id=plugin.pd.identifier, plugin_id=plugin.id, grade_manager_id=1)
    shim.remove_user_all_roles(plugin, ["foo"])

    assert iam_management_client.management_delete_grade_manager_members.called
    assert iam_management_client.v2_management_delete_group_members.called


def test_fetch_plugin_members(plugin, iam_management_client):
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.ADMINISTRATOR, user_group_id=1)
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.DEVELOPER, user_group_id=2)
    assert shim.fetch_plugin_members(plugin) == cattr.structure(
        [
            {
                "username": "admin",
                "role": {
                    "id": PluginRole.ADMINISTRATOR,
                    "name": PluginRole.get_choice_label(PluginRole.ADMINISTRATOR),
                },
            },
            {
                "username": "admin",
                "role": {"id": PluginRole.DEVELOPER, "name": PluginRole.get_choice_label(PluginRole.DEVELOPER)},
            },
            {
                "username": "foo",
                "role": {"id": PluginRole.DEVELOPER, "name": PluginRole.get_choice_label(PluginRole.DEVELOPER)},
            },
            {
                "username": "bar",
                "role": {"id": PluginRole.DEVELOPER, "name": PluginRole.get_choice_label(PluginRole.DEVELOPER)},
            },
        ],
        List[shim.PluginMember],
    )

    assert iam_management_client.v2_management_group_members.called


def test_setup_builtin_grade_manager(plugin, iam_management_client):
    grade_manager = G(PluginGradeManager, pd_id=plugin.pd.identifier, plugin_id=plugin.id, grade_manager_id=1)
    shim.setup_builtin_grade_manager(plugin)
    assert not iam_management_client.management_grade_managers.called

    grade_manager.delete()
    shim.setup_builtin_grade_manager(plugin)
    assert iam_management_client.management_grade_managers.called


def test_setup_builtin_user_groups(plugin, iam_management_client):
    G(PluginGradeManager, pd_id=plugin.pd.identifier, plugin_id=plugin.id, grade_manager_id=1)
    shim.setup_builtin_user_groups(plugin)

    assert iam_management_client.v2_management_grade_manager_create_groups.called
    assert iam_management_client.v2_management_groups_policies_grant.called
    assert PluginUserGroup.objects.filter_by_plugin(plugin).get(role=PluginRole.ADMINISTRATOR).user_group_id == 1
    assert PluginUserGroup.objects.filter_by_plugin(plugin).get(role=PluginRole.DEVELOPER).user_group_id == 2


def test_delete_builtin_user_groups(plugin, iam_management_client):
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.ADMINISTRATOR, user_group_id=1)
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.DEVELOPER, user_group_id=2)
    assert PluginUserGroup.objects.filter_by_plugin(plugin).count() == 2

    shim.delete_builtin_user_groups(plugin)
    assert iam_management_client.v2_management_grade_manager_delete_group.called
    assert PluginUserGroup.objects.filter_by_plugin(plugin).count() == 0
