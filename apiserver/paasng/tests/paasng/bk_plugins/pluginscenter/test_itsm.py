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

import json
from unittest import mock

import pytest
import requests

from paasng.bk_plugins.pluginscenter.constants import PluginReleaseStatus, PluginRole
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ApprovalServiceName
from paasng.bk_plugins.pluginscenter.itsm_adaptor.utils import (
    add_approver_to_plugin_admins,
    get_ticket_status,
    submit_online_approval_ticket,
)

pytestmark = pytest.mark.django_db


@pytest.fixture()
def _set_itsm_to_current_stage(release, itsm_online_stage):
    release.current_stage = itsm_online_stage
    release.save(update_fields=["current_stage"])


@pytest.fixture()
def mock_client_session():
    with mock.patch("bkapi_client_core.session.Session.request") as mocked_request:
        yield mocked_request


@pytest.mark.usefixtures("_set_itsm_to_current_stage")
def test_execute_itsm_stage(mock_client_session, online_approval_service, pd, plugin, release, bk_user):
    """测试执行 itsm 阶段"""
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"data": {"sn": "sn1"}, "code": 0}'
    mock_client_session.return_value = response

    submit_online_approval_ticket(pd, plugin, release, bk_user.username)
    assert mock_client_session.called

    assert release.current_stage.status == PluginReleaseStatus.PENDING
    assert release.current_stage.itsm_detail.sn == "sn1"


@pytest.mark.usefixtures("_set_itsm_to_current_stage")
def test_itsm_render(mock_client_session):
    itsm_ticket_status_resp = {
        "code": 0,
        "message": "",
        "data": {
            "ticket_url": "https://blueking.com/#/commonInfo?id=6&activeNname=all&router=request",
            "operations": [
                {"can_operate": True, "name": "撤单", "key": "WITHDRAW"},
                {"can_operate": True, "name": "恢复", "key": "UNSUSPEND"},
            ],
            "current_status": "SUSPENDED",
        },
    }

    response = requests.Response()
    response.status_code = 200

    res_content = json.dumps(itsm_ticket_status_resp)
    response._content = res_content.encode()
    mock_client_session.return_value = response

    sn = "sn1"
    ticket_info = get_ticket_status(sn)
    assert mock_client_session.called

    assert ticket_info["current_status_display"] == "被挂起"
    assert ticket_info["can_withdraw"] is True


@pytest.mark.parametrize(
    ("service_name", "expected_leader", "expected_admins", "sync_members_mock"),
    [
        # 可见范围修改：将平台管理员添加到插件管理员中
        (ApprovalServiceName.VISIBLE_RANGE_APPROVAL, None, ["admin1", "admin2"], True),
        # 全量审批：将平台管理员添加到插件管理员中
        (ApprovalServiceName.CODECC_FULL_RELEASE_APPROVAL, None, ["admin1", "admin2"], True),
        # 灰度审批（含组织）：将提单者上级添加到插件开发者中
        (ApprovalServiceName.CODECC_ORG_GRAY_RELEASE_APPROVAL, ["leader_user"], None, True),
        # 灰度审批（不含组织）：不需要新增管理员
        (ApprovalServiceName.CODECC_GRAY_RELEASE_APPROVAL, None, None, False),
    ],
)
def test_add_approver_as_member(mocker, plugin, service_name, expected_leader, expected_admins, sync_members_mock):
    """插件的 MemberShip 表已经删除，无法像应用一样将 iam 操作 mock 为 DB 操作，直接验证相关条件下对应的函数是否正确调用"""
    if expected_leader:
        mock_get_leader = mocker.patch(
            "paasng.bk_plugins.pluginscenter.itsm_adaptor.utils._get_leader_by_user", return_value=expected_leader
        )

    # Mocking members API to return existing members
    mock_members = [mock.MagicMock(username="existing_user", role=mock.MagicMock(id=PluginRole.ADMINISTRATOR))]
    mocker.patch(
        "paasng.bk_plugins.pluginscenter.itsm_adaptor.utils.members_api.fetch_plugin_members",
        return_value=mock_members,
    )

    # Mock members_api methods for removing and adding roles
    mock_remove_roles = mocker.patch(
        "paasng.bk_plugins.pluginscenter.itsm_adaptor.utils.members_api.remove_user_all_roles"
    )
    mock_add_roles = mocker.patch("paasng.bk_plugins.pluginscenter.itsm_adaptor.utils.members_api.add_role_members")

    # Mocking sync_members if required
    if sync_members_mock:
        mock_sync_members = mocker.patch("paasng.bk_plugins.pluginscenter.itsm_adaptor.utils.sync_members")

    # Setting the plugin administrators
    if expected_admins:
        plugin.pd.administrator = expected_admins

    # Call the function
    add_approver_to_plugin_admins(plugin, service_name, "operator_user")

    # Verify the leader fetching function was called
    if expected_leader:
        mock_get_leader.assert_called_once_with("operator_user")

    # Verify that the correct roles are removed and added
    if expected_leader:
        mock_add_roles.assert_called_once_with(plugin, role=PluginRole.DEVELOPER, usernames=expected_leader)
    elif expected_admins:
        # 使用集合校验参数内容，忽略顺序
        mock_remove_roles.assert_called_once_with(plugin, mock.ANY)
        args, _ = mock_remove_roles.call_args
        assert set(args[1]) == set(expected_admins)
        mock_add_roles.assert_called_once_with(plugin, role=PluginRole.ADMINISTRATOR, usernames=mock.ANY)

    # Verify sync_members was called
    if sync_members_mock:
        mock_sync_members.assert_called_once_with(pd=plugin.pd, instance=plugin)
