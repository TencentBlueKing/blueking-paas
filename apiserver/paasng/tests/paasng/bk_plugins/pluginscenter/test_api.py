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

from paasng.bk_plugins.pluginscenter.constants import PluginReleaseStatus, PluginStatus
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ItsmTicketStatus
from paasng.bk_plugins.pluginscenter.itsm_adaptor.open_apis.views import PluginCallBackApiViewSet
from paasng.bk_plugins.pluginscenter.models.instances import (
    ItsmDetail,
    PluginRelease,
    PluginVisibleRange,
)

pytestmark = pytest.mark.django_db
PluginCallBackApiViewSet.authentication_classes = []  # type: ignore

CALLBACK_DATA = {
    "title": "标题",
    "current_status": "",
    "sn": "sn1",
    "ticket_url": "单据链接",
    "update_at": "单据更新时间",
    "updated_by": "单据更新人",
    "approve_result": "",
    "token": "token",
    "last_approver": "最后一个节点的审批人",
}


@pytest.fixture(autouse=True)
def thirdparty_client(thirdparty_client):
    return thirdparty_client


class TestArchived:
    @pytest.fixture()
    def plugin(self, plugin):
        plugin.status = PluginStatus.ARCHIVED
        plugin.save()
        return plugin

    @pytest.mark.usefixtures("_setup_bk_user")
    def test_readonly_api(self, api_client, pd, plugin, release, iam_policy_client):
        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/"
        resp = api_client.get(url)
        data = resp.json()
        assert resp.status_code == 200
        assert data["overview_page"]["top_url"].find(str(plugin.id)) > 0

    @pytest.mark.usefixtures("_setup_bk_user")
    def test_update_api(self, api_client, pd, plugin, release, iam_policy_client):
        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/"
        resp = api_client.post(url)
        assert resp.status_code == 400
        # 已经下架的操作还可以操作
        assert resp.json()["detail"] != error_codes.PLUGIN_ARCHIVED.message


class TestPluginApi:
    @pytest.mark.parametrize(
        ("is_current_stage", "update_status", "status_code", "stage_status"),
        [
            (False, PluginReleaseStatus.SUCCESSFUL.value, 400, ""),
            (True, PluginReleaseStatus.SUCCESSFUL.value, 200, PluginReleaseStatus.SUCCESSFUL.value),
            (True, PluginReleaseStatus.FAILED.value, 200, PluginReleaseStatus.FAILED.value),
        ],
    )
    @pytest.mark.usefixtures("_setup_bk_user")
    def test_update_status(
        self,
        api_client,
        pd,
        plugin,
        release,
        subpage_stage,
        is_current_stage,
        update_status,
        status_code,
        stage_status,
        iam_policy_client,
    ):
        if is_current_stage:
            release.current_stage = subpage_stage
            release.save()

        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/{release.id}/stages/{subpage_stage.stage_id}/status/"
        resp = api_client.post(url, data={"status": update_status})
        assert resp.status_code == status_code
        if resp.status_code == 200:
            assert resp.json()["status"] == stage_status

    @pytest.mark.usefixtures("_setup_bk_user")
    def test_update_publisher(self, api_client, pd, plugin, iam_policy_client):
        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/publisher/"

        resp = api_client.post(url, data={"publisher": "xxxxx"})
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        (
            "is_in_approval",
            "status_code",
        ),
        [
            (False, 200),
            (True, 400),
        ],
    )
    @pytest.mark.usefixtures("_setup_bk_user")
    def test_update_visible_range(
        self, api_client, pd, plugin, is_in_approval, status_code, iam_policy_client, visible_range_approval_service
    ):
        PluginVisibleRange.objects.update_or_create(plugin=plugin, defaults={"is_in_approval": is_in_approval})

        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/visible_range/"

        with mock.patch(
            "paasng.bk_plugins.pluginscenter.itsm_adaptor.client.ItsmClient.create_ticket",
            return_value=ItsmDetail(fields=[], sn="1111", ticket_url="http://1111"),
        ):
            resp = api_client.post(
                url,
                data={
                    "bkci_project": ["1111", "22222"],
                    "organization": [
                        {"id": 1, "type": "user", "name": "admin", "display_name": "admin"},
                        {
                            "id": 3,
                            "type": "department",
                            "name": "xxxx部门",
                            "display_name": "xxxx部门",
                        },
                    ],
                },
            )
        assert resp.status_code == status_code
        if status_code == 200:
            assert resp.json()["is_in_approval"] is True

    @pytest.mark.parametrize(
        (
            "itsm_ticket_status",
            "status_code",
        ),
        [
            ("RUNNING", 400),
            ("FINISHED", 200),
        ],
    )
    @pytest.mark.usefixtures("_setup_bk_user")
    def test_upadate_release_strategy(
        self,
        api_client,
        pd,
        plugin,
        release_strategy,
        itsm_ticket_status,
        status_code,
        iam_policy_client,
        gray_release_approval_service,
    ):
        release_strategy.itsm_detail = ItsmDetail(fields=[], sn="222", ticket_url="http://222")
        release_strategy.save()
        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/{release_strategy.release.id}/strategy/"
        with mock.patch(
            "paasng.bk_plugins.pluginscenter.itsm_adaptor.client.ItsmClient.create_ticket",
            return_value=ItsmDetail(fields=[], sn="1111", ticket_url="http://1111"),
        ), mock.patch(
            "paasng.bk_plugins.pluginscenter.itsm_adaptor.client.ItsmClient.get_ticket_status",
            return_value={"ticket_url": "https://xxxx", "current_status": itsm_ticket_status},
        ):
            resp = api_client.post(
                url,
                data={
                    "strategy": "gray",
                    "bkci_project": ["1111", "22222"],
                    "organization": [
                        {"id": 1, "type": "user", "name": "admin", "display_name": "admin"},
                        {
                            "id": 3,
                            "type": "department",
                            "name": "xxxx部门",
                            "display_name": "xxxx部门",
                        },
                    ],
                },
            )
        assert resp.status_code == status_code

    @pytest.mark.parametrize(
        (
            "release_status",
            "status_code",
        ),
        [
            (PluginReleaseStatus.SUCCESSFUL.value, 200),
            (PluginReleaseStatus.FAILED.value, 400),
            (PluginReleaseStatus.PENDING.value, 400),
        ],
    )
    @pytest.mark.usefixtures("_setup_bk_user")
    def test_rollback_release(
        self,
        api_client,
        pd,
        plugin,
        release,
        release_status,
        status_code,
        iam_policy_client,
    ):
        # 更新版本的状态，只有发布成功的版本才能回滚
        release.status = release_status
        release.save()
        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/releases/{release.id}/rollback/"
        resp = api_client.post(url)
        assert resp.status_code == status_code
        if status_code == 200:
            assert resp.json()["is_rolled_back"] is True


class TestSysApis:
    @pytest.mark.parametrize(
        ("current_status", "approve_result", "stage_status"),
        [
            (ItsmTicketStatus.FINISHED.value, True, PluginReleaseStatus.SUCCESSFUL.value),
            (ItsmTicketStatus.FINISHED.value, False, PluginReleaseStatus.FAILED.value),
            (ItsmTicketStatus.TERMINATED.value, False, PluginReleaseStatus.INTERRUPTED.value),
            (ItsmTicketStatus.REVOKED.value, True, PluginReleaseStatus.INTERRUPTED.value),
        ],
    )
    def test_itsm_online_callback(
        self, api_client, pd, plugin, release, itsm_online_stage, current_status, approve_result, stage_status
    ):
        callback_url = (
            "/open/api/itsm/bkplugins/"
            + f"{pd.identifier}/plugins/{plugin.id}/releases/{release.id}/stages/{itsm_online_stage.id}/"
        )

        callback_data = CALLBACK_DATA
        callback_data["current_status"] = current_status
        callback_data["approve_result"] = approve_result

        resp_data = api_client.post(callback_url, callback_data).json()

        assert resp_data["code"] == 0
        assert resp_data["result"] is True
        stage = release.all_stages.get(id=itsm_online_stage.id)
        assert stage.status == stage_status

    @pytest.mark.parametrize(
        ("current_status", "approve_result", "plugin_status"),
        [
            (ItsmTicketStatus.FINISHED.value, False, PluginStatus.APPROVAL_FAILED.value),
            (ItsmTicketStatus.TERMINATED.value, False, PluginStatus.APPROVAL_FAILED.value),
            (ItsmTicketStatus.REVOKED.value, True, PluginStatus.APPROVAL_FAILED.value),
        ],
    )
    def test_itsm_create_callback(self, api_client, pd, plugin, current_status, approve_result, plugin_status):
        callback_url = "/open/api/itsm/bkplugins/" + f"{pd.identifier}/plugins/{plugin.id}/"

        callback_data = CALLBACK_DATA
        callback_data["current_status"] = current_status
        callback_data["approve_result"] = approve_result
        resp_data = api_client.post(callback_url, callback_data).json()

        assert resp_data["code"] == 0
        assert resp_data["result"] is True
        plugin.refresh_from_db()
        assert plugin.status == plugin_status

    @pytest.mark.parametrize(
        ("current_status", "approve_result", "is_in_approval", "is_data_updated"),
        [
            # 单据结束、审批结果为不同意：可见范围的审批状态设为 False，但是不更新可见范围的数据
            (ItsmTicketStatus.FINISHED.value, False, False, False),
            # 单据结束、审批结果为同意：可见范围的审批状态设为 False，且更新可见范围的数据
            (ItsmTicketStatus.FINISHED.value, True, False, True),
            # # 单据未结束：可见范围的审批状态设为 False，也不更新可见范围的数据
            (ItsmTicketStatus.RUNNING.value, False, True, False),
            (ItsmTicketStatus.SUSPENDED.value, True, True, False),
        ],
    )
    def test_itsm_visible_range_callback(
        self, api_client, pd, plugin, current_status, approve_result, is_in_approval, is_data_updated
    ):
        new_bkci_project = ["11111", "22222", "33333"]
        new_organization = [
            {"id": 1, "type": "user", "name": "admin", "display_name": "admin"},
            {
                "id": 3,
                "type": "department",
                "name": "xxxx部门",
                "display_name": "xxxx部门",
            },
        ]
        visible_range_obj, _ = PluginVisibleRange.objects.update_or_create(
            plugin=plugin,
            defaults={
                "itsm_detail": ItsmDetail(
                    fields=[
                        {"key": "origin_bkci_project", "value": new_bkci_project},
                        {"key": "origin_organization", "value": new_organization},
                    ],
                    sn="1111",
                    ticket_url="http://1111",
                )
            },
        )
        callback_url = "/open/api/itsm/bkplugins/" + f"{pd.identifier}/plugins/{plugin.id}/visible_range/"

        callback_data = CALLBACK_DATA
        callback_data["current_status"] = current_status
        callback_data["approve_result"] = approve_result
        resp_data = api_client.post(callback_url, callback_data).json()

        assert resp_data["code"] == 0
        assert resp_data["result"] is True

        visible_range_obj.refresh_from_db()
        assert visible_range_obj.is_in_approval == is_in_approval
        if is_data_updated:
            assert visible_range_obj.bkci_project == new_bkci_project
            assert visible_range_obj.organization == new_organization
        else:
            assert visible_range_obj.bkci_project != new_bkci_project
            assert visible_range_obj.organization != new_organization

    @pytest.mark.parametrize(
        ("strategy", "current_status", "approve_result", "release_status"),
        [
            # 全量发布： 单据结束、审批结果为不同意， 则版本发布失败
            ("full", ItsmTicketStatus.FINISHED.value, False, "failed"),
            # 全量发布： 单据结束、审批结果为不同意， 则版本发布成功
            ("full", ItsmTicketStatus.FINISHED.value, True, "successful"),
            # 灰度发布： 单据结束、审批结果为不同意， 版本状态为发布中
            ("gray", ItsmTicketStatus.FINISHED.value, False, "failed"),
            # 灰度发布： 单据结束、审批结果为不同意， 版本状态为发布中
            ("gray", ItsmTicketStatus.FINISHED.value, True, "pending"),
        ],
    )
    def test_itsm_canry_release_callback(
        self, api_client, pd, plugin, release_strategy, current_status, approve_result, strategy, release_status
    ):
        release_strategy.strategy = strategy
        release_strategy.save()
        callback_url = (
            "/open/api/itsm/bkplugins/"
            + f"{pd.identifier}/plugins/{plugin.id}/releases/{release_strategy.release.id}/strategy/{release_strategy.id}/"
        )

        callback_data = CALLBACK_DATA
        callback_data["current_status"] = current_status
        callback_data["approve_result"] = approve_result
        resp_data = api_client.post(callback_url, callback_data).json()

        assert resp_data["code"] == 0
        assert resp_data["result"] is True

        release = PluginRelease.objects.get(id=release_strategy.release.id)
        assert release.status == release_status
