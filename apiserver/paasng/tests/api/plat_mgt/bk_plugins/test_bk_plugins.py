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
from django.urls import reverse
from django_dynamic_fixture import G

from paasng.bk_plugins.pluginscenter.constants import PluginRevisionType, PluginRole
from paasng.bk_plugins.pluginscenter.iam_adaptor.models import PluginGradeManager, PluginUserGroup
from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance
from paasng.plat_mgt.bk_plugins.views import is_user_plugin_admin

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mock_iam_client():
    from tests.utils.mocks.iam import StubBKIAMClient

    with (
        mock.patch("paasng.infras.iam.helpers.BKIAMClient", new=StubBKIAMClient),
        mock.patch("paasng.infras.iam.client.BKIAMClient", new=StubBKIAMClient),
        mock.patch("paasng.bk_plugins.pluginscenter.iam_adaptor.management.shim.BKIAMClient", new=StubBKIAMClient),
    ):
        yield


class TestBKPluginMembersManageViewSet:
    """测试 BK 插件成员管理相关接口"""

    @pytest.fixture
    def create_plugin_instance(self, bk_plugin_app):
        """创建一个 BK 插件实例"""
        # 创建插件定义
        plugin_definition = G(
            PluginDefinition,
            identifier="test-plugin-type",
            release_revision={
                "revisionType": PluginRevisionType.MASTER,
                "versionNo": "automatic",
                "revisionPattern": None,
                "revisionPolicy": None,
                "reportFormat": None,
                "releaseResultFormat": None,
                "docs": None,
                "extraFields": {},
            },
            # 添加 release_stages
            release_stages=[],
        )

        # 创建插件实例
        plugin_instance = G(
            PluginInstance,
            pd=plugin_definition,
            id=bk_plugin_app.code,
            template={
                "id": "python-template",
                "name": "Python模板",
                "language": "Python",
                "repository": "https://github.com/example/template.git",
            },
            tenant_id="system",
        )

        G(
            PluginGradeManager,
            pd_id=plugin_definition.identifier,
            plugin_id=plugin_instance.id,
            grade_manager_id=1,
            tenant_id="default",
        )

        # 创建用户组
        G(
            PluginUserGroup,
            pd_id=plugin_definition.identifier,
            plugin_id=plugin_instance.id,
            role=PluginRole.ADMINISTRATOR,
            user_group_id=1,
            tenant_id="default",
        )

        return plugin_instance

    def test_become_admin(self, plat_manager_user, bk_plugin_app, plat_mgt_api_client, create_plugin_instance):
        """测试 BK 插件添加管理员"""
        # 应用租户与插件租户一致
        url = reverse("plat_mgt.applications.plugin.members.admin", kwargs={"app_code": bk_plugin_app.code})
        resp = plat_mgt_api_client.post(url)
        print(resp.data)
        assert resp.status_code == 200

        # 检查用户是否被添加为管理员
        assert is_user_plugin_admin(bk_plugin_app.code, plat_manager_user.username)

    def test_become_admin_different_tenant(self, bk_plugin_app, plat_mgt_api_client, create_plugin_instance):
        """测试 BK 插件添加管理员，应用租户与插件租户不一致"""
        # 修改插件实例的租户
        create_plugin_instance.tenant_id = "other_tenant"
        create_plugin_instance.save()

        url = reverse("plat_mgt.applications.plugin.members.admin", kwargs={"app_code": bk_plugin_app.code})
        resp = plat_mgt_api_client.post(url)
        assert resp.status_code == 400

    def test_remove_admin(self, plat_manager_user, bk_plugin_app, plat_mgt_api_client, create_plugin_instance):
        """测试 BK 插件退出管理员"""

        # 使用接口前，先添加用户为管理员
        url = reverse("plat_mgt.applications.plugin.members.admin", kwargs={"app_code": bk_plugin_app.code})
        resp = plat_mgt_api_client.post(url)
        print(resp.data)
        assert resp.status_code == 200

        # 现在测试退出管理员
        resp = plat_mgt_api_client.delete(url)
        assert resp.status_code == 204
        assert not is_user_plugin_admin(bk_plugin_app.code, plat_manager_user.username)
