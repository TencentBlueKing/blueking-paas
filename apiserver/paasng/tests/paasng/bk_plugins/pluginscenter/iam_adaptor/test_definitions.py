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

from paasng.bk_plugins.pluginscenter.iam_adaptor.constants import PluginRole
from paasng.bk_plugins.pluginscenter.iam_adaptor.definitions import (
    gen_iam_grade_manager,
    gen_iam_resource,
    gen_iam_resource_name,
    gen_plugin_user_group,
)

pytestmark = pytest.mark.django_db


def test_gen_iam_resource_name(plugin):
    assert gen_iam_resource_name(plugin) == f"{plugin.name}({plugin.id})"


def test_gen_iam_resource(plugin):
    plugin_resource = gen_iam_resource(plugin)
    assert plugin_resource.id == f"{plugin.pd.identifier}:{plugin.id}"
    assert plugin_resource.name == gen_iam_resource_name(plugin)
    assert plugin_resource.admin == plugin.creator.username


def test_gen_iam_grade_manager(pd, plugin):
    grade_manager = gen_iam_grade_manager(plugin)
    assert grade_manager.name == f"{plugin.pd.name}:{plugin.id}"
    assert (
        grade_manager.description
        == f"{pd.name}（{gen_iam_resource_name(plugin)}）分级管理员，拥有审批用户加入管理者/开发者用户组权限。"
    )


@pytest.mark.parametrize(
    ("role", "name", "description"),
    [
        (
            PluginRole.ADMINISTRATOR,
            "{pd_name}-{plugin_name}-管理者",
            "{pd_name}（{plugin_name}）管理者，拥有应用的全部权限。",
        ),
        (
            PluginRole.DEVELOPER,
            "{pd_name}-{plugin_name}-开发者",
            "{pd_name}（{plugin_name}）开发者，拥有应用的开发权限，如基础开发，版本发布等。",
        ),
    ],
)
def test_gen_plugin_user_group(pd, plugin, role, name, description):
    group = gen_plugin_user_group(plugin, role)
    assert group.role == role
    assert group.name == name.format(pd_name=pd.name, plugin_name=plugin.name)
    assert group.description == description.format(pd_name=pd.name, plugin_name=plugin.name)
    assert group.id is None
