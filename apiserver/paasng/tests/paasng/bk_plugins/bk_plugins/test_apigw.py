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

from unittest.mock import MagicMock, patch

import pytest
from bkapi_client_core.exceptions import BKAPIError
from django_dynamic_fixture import G

from paasng.bk_plugins.bk_plugins.apigw import (
    PluginDefaultAPIGateway,
    safe_remove_apigw_maintainers,
    safe_sync_apigw,
    safe_sync_apigw_maintainers,
    set_distributors,
)
from paasng.bk_plugins.bk_plugins.exceptions import PluginApiGatewayServiceError
from paasng.bk_plugins.bk_plugins.models import BkPluginDistributor
from paasng.infras.iam.helpers import add_role_members
from paasng.platform.applications.constants import ApplicationRole

pytestmark = pytest.mark.django_db


@pytest.fixture()
def fake_good_client():
    """Make a fake client which produce successful result"""
    fake_client = MagicMock()
    fake_client.sync_api.return_value = {
        "data": {"id": 1, "name": "foo"},
        "code": 0,
        "result": True,
        "message": "OK",
    }
    empty_payload = {"data": None, "code": 0, "result": True, "message": ""}
    fake_client.grant_permissions.return_value = empty_payload
    fake_client.revoke_permissions.return_value = empty_payload
    fake_client.update_gateway_status.return_value = empty_payload
    return fake_client


@pytest.fixture()
def fake_bad_client():
    """Make a fake client which produce failed result"""
    fake_client = MagicMock()
    fake_client.sync_api.side_effect = BKAPIError("foo error")
    fake_client.grant_permissions.side_effect = BKAPIError("foo error")
    fake_client.revoke_permissions.side_effect = BKAPIError("foo error")
    fake_client.update_gateway_status.side_effect = BKAPIError("foo error")
    return fake_client


class TestPluginDefaultAPIGateway:
    def test_sync_succeeded(self, bk_plugin_app, fake_good_client):
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_id = apigw_service.sync()

        assert apigw_id == 1
        assert fake_good_client.sync_api.called
        _, kwargs = fake_good_client.sync_api.call_args_list[0]
        assert len(kwargs["data"]["maintainers"]) > 0

    def test_sync_failed(self, bk_plugin_app, fake_bad_client):
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_bad_client)
        with pytest.raises(PluginApiGatewayServiceError):
            _ = apigw_service.sync()

    def test_sync_reuse_apigw_name(self, bk_plugin_app, fake_good_client):
        bk_plugin_app.bk_plugin_profile.api_gw_name = "updated_name"
        bk_plugin_app.bk_plugin_profile.save()

        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_service.sync()

        _, kwargs = fake_good_client.sync_api.call_args_list[0]
        assert kwargs["data"]["name"] == "updated_name", "`sync()` should reuse the name of synced gateway"

    def test_grant_succeeded(self, bk_plugin_app, fake_good_client):
        distributor = G(BkPluginDistributor, code_name="sample-dis-1", bk_app_code="sample-dis-1")
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_service.grant(distributor)
        assert fake_good_client.grant_permissions.called

    def test_revoke_succeeded(self, bk_plugin_app, fake_good_client):
        distributor = G(BkPluginDistributor, code_name="sample-dis-1", bk_app_code="sample-dis-1")
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_service.revoke(distributor)
        assert fake_good_client.revoke_permissions.called

    def test_update_status_succeeded(self, bk_plugin_app, fake_good_client):
        apigw_service = PluginDefaultAPIGateway(bk_plugin_app, client=fake_good_client)
        apigw_service.update_gateway_status(True)
        assert fake_good_client.update_gateway_status.called


def test_safe_sync_apigw_succeeded(bk_plugin_app, fake_good_client):
    with patch(
        "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
        return_value=fake_good_client,
    ):
        safe_sync_apigw(bk_plugin_app)
        assert isinstance(bk_plugin_app.bk_plugin_profile.api_gw_id, int)


def test_safe_sync_apigw_failed(bk_plugin_app, fake_bad_client):
    with patch(
        "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
        return_value=fake_bad_client,
    ):
        safe_sync_apigw(bk_plugin_app)
        assert bk_plugin_app.bk_plugin_profile.api_gw_id is None


class TestSafeSyncApigwMaintainers:
    """成员变更后刷新网关维护者的容错入口"""

    def test_skip_when_not_synced(self, bk_plugin_app, fake_good_client):
        # 网关未创建（未首次部署）时应跳过，不调用 sync_api
        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_good_client,
        ):
            safe_sync_apigw_maintainers(bk_plugin_app)
            assert fake_good_client.sync_api.called is False

    def test_refresh_when_synced(self, bk_plugin_app, fake_good_client):
        # 网关已创建时应调用 sync() 全量覆盖 maintainers
        bk_plugin_app.bk_plugin_profile.api_gw_id = 1
        bk_plugin_app.bk_plugin_profile.save()
        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_good_client,
        ):
            safe_sync_apigw_maintainers(bk_plugin_app)
            assert fake_good_client.sync_api.called is True
            _, kwargs = fake_good_client.sync_api.call_args_list[0]
            assert len(kwargs["data"]["maintainers"]) > 0

    def test_tolerate_sync_error(self, bk_plugin_app, fake_bad_client):
        # 网关同步失败应被捕获，不向上抛出、不阻塞主流程
        bk_plugin_app.bk_plugin_profile.api_gw_id = 1
        bk_plugin_app.bk_plugin_profile.save()
        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_bad_client,
        ):
            safe_sync_apigw_maintainers(bk_plugin_app)


class TestSafeRemoveApigwMaintainers:
    """成员减少后, 从网关维护人名单中移除这些人

    网关的 sync 更新分支只做并集, 无法完成移除, 因此必须显式调用删除接口。
    """

    @pytest.fixture()
    def synced_app(self, bk_plugin_app):
        """网关已创建（已首次部署）的插件应用"""
        bk_plugin_app.bk_plugin_profile.api_gw_id = 1
        bk_plugin_app.bk_plugin_profile.api_gw_name = "bp-foo"
        bk_plugin_app.bk_plugin_profile.save()
        return bk_plugin_app

    @pytest.fixture()
    def delete(self, mocker):
        """替换网关删除调用, 关注最终提交给网关的名单"""
        return mocker.patch(
            "paasng.bk_plugins.bk_plugins.apigw.ApiGatewayClient.delete_gateway_maintainers",
            return_value=[],
        )

    def test_skip_when_not_synced(self, bk_plugin_app, delete):
        """网关尚未创建时无需删除"""
        safe_remove_apigw_maintainers(bk_plugin_app, ["leaver"])

        delete.assert_not_called()

    def test_remove_when_no_maintainer_role_remains(self, synced_app, delete):
        """退出后不再具备管理员/开发者角色时, 应移除网关维护人"""
        safe_remove_apigw_maintainers(synced_app, ["leaver"])

        delete.assert_called_once_with(gateway_name="bp-foo", maintainers=["leaver"])

    def test_keep_when_still_developer(self, synced_app, delete):
        """仍保留开发者角色时, 用户还在网关维护人名单内, 不应移除"""
        add_role_members(synced_app.code, ApplicationRole.DEVELOPER, "leaver")

        safe_remove_apigw_maintainers(synced_app, ["leaver"])

        delete.assert_not_called()

    def test_keep_when_still_administrator(self, synced_app, delete):
        """仍保留管理员角色时, 不应移除"""
        add_role_members(synced_app.code, ApplicationRole.ADMINISTRATOR, "leaver")

        safe_remove_apigw_maintainers(synced_app, ["leaver"])

        delete.assert_not_called()

    def test_remove_when_only_operator_remains(self, synced_app, delete):
        """只残留运营者角色时, 该用户不在网关维护人名单内, 仍应移除"""
        add_role_members(synced_app.code, ApplicationRole.OPERATOR, "leaver")

        safe_remove_apigw_maintainers(synced_app, ["leaver"])

        delete.assert_called_once_with(gateway_name="bp-foo", maintainers=["leaver"])

    def test_only_remove_users_without_maintainer_role(self, synced_app, delete):
        """批量移除时只提交仍不具备维护人角色的用户, 且合并为一次请求"""
        add_role_members(synced_app.code, ApplicationRole.DEVELOPER, "still-dev")

        safe_remove_apigw_maintainers(synced_app, ["leaver", "still-dev"])

        delete.assert_called_once_with(gateway_name="bp-foo", maintainers=["leaver"])


class TestSetDistributors:
    @pytest.fixture
    def distributors(self):
        dis_1 = G(BkPluginDistributor, code_name="sample-dis-1", bk_app_code="sample-dis-1")
        dis_2 = G(BkPluginDistributor, code_name="sample-dis-2", bk_app_code="sample-dis-2")
        return dis_1, dis_2

    def test_grant_distributor_success(self, bk_plugin_app, fake_good_client, distributors):
        """测试授权成功"""
        dis_1, _ = distributors
        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_good_client,
        ):
            # 首次授权
            from paasng.bk_plugins.bk_plugins.apigw import grant_distributor

            grant_distributor(bk_plugin_app, dis_1)

            assert bk_plugin_app.distributors.count() == 1
            assert fake_good_client.grant_permissions.call_count == 1

    def test_grant_existing_distributor(self, bk_plugin_app, fake_good_client, distributors):
        """测试重复授权同一插件使用方"""
        dis_1, _ = distributors
        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_good_client,
        ):
            from paasng.bk_plugins.bk_plugins.apigw import grant_distributor

            # 两次授权同一分发者
            grant_distributor(bk_plugin_app, dis_1)
            grant_distributor(bk_plugin_app, dis_1)

            # 应该只调用一次授权API
            assert fake_good_client.grant_permissions.call_count == 1

    def test_revoke_distributor_success(self, bk_plugin_app, fake_good_client, distributors):
        """测试取消授权成功"""
        dis_1, _ = distributors
        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_good_client,
        ):
            from paasng.bk_plugins.bk_plugins.apigw import revoke_distributor

            # 先授权再取消
            bk_plugin_app.distributors.add(dis_1)
            revoke_distributor(bk_plugin_app, dis_1)

            assert bk_plugin_app.distributors.count() == 0
            assert fake_good_client.revoke_permissions.call_count == 1

    def test_revoke_non_existing_distributor(self, bk_plugin_app, fake_good_client, distributors):
        """测试取消未授权的插件使用方"""
        dis_1, _ = distributors
        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_good_client,
        ):
            from paasng.bk_plugins.bk_plugins.apigw import revoke_distributor

            revoke_distributor(bk_plugin_app, dis_1)

            # 不应该调用取消授权API
            assert fake_good_client.revoke_permissions.call_count == 0

    def test_grant_with_api_failure(self, bk_plugin_app, fake_bad_client, distributors):
        """测试API调用失败时的授权异常"""
        dis_1, _ = distributors
        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_bad_client,
        ):
            from paasng.bk_plugins.bk_plugins.apigw import grant_distributor

            with pytest.raises(RuntimeError):
                grant_distributor(bk_plugin_app, dis_1)

    @pytest.mark.usefixtures("_init_tmpls")
    def test_integrated(self, bk_plugin_app, fake_good_client):
        dis_1 = G(BkPluginDistributor, code_name="sample-dis-1", bk_app_code="sample-dis-1")
        dis_2 = G(BkPluginDistributor, code_name="sample-dis-2", bk_app_code="sample-dis-2")

        with patch(
            "paasng.bk_plugins.bk_plugins.apigw.PluginDefaultAPIGateway._make_api_client",
            return_value=fake_good_client,
        ):
            safe_sync_apigw(bk_plugin_app)
            set_distributors(bk_plugin_app, [dis_1])
            set_distributors(bk_plugin_app, [dis_1, dis_2])
            assert bk_plugin_app.distributors.count() == 2

            set_distributors(bk_plugin_app, [])
            assert bk_plugin_app.distributors.count() == 0

            # Grant permissions should be called twice
            call_args_list = fake_good_client.grant_permissions.call_args_list
            assert len(call_args_list) == 2
            assert sorted([kwargs["data"]["target_app_code"] for _, kwargs in call_args_list]) == [
                dis_1.bk_app_code,
                dis_2.bk_app_code,
            ]

            # Revoke permissions should be called twice
            call_args_list = fake_good_client.revoke_permissions.call_args_list
            assert len(call_args_list) == 2
            assert sorted([kwargs["data"]["target_app_codes"] for _, kwargs in call_args_list]) == [
                [dis_1.bk_app_code],
                [dis_2.bk_app_code],
            ]
