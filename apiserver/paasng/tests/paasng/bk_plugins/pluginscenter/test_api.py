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
import pytest

from paasng.bk_plugins.pluginscenter.constants import PluginReleaseStatus, PluginStatus
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ItsmTicketStatus
from paasng.bk_plugins.pluginscenter.itsm_adaptor.open_apis.views import PluginCallBackApiViewSet

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
    yield thirdparty_client


class TestArchived:
    @pytest.fixture
    def plugin(self, plugin):
        plugin.status = PluginStatus.ARCHIVED
        plugin.save()
        return plugin

    def test_readonly_api(self, api_client, pd, plugin, release, iam_policy_client, setup_bk_user):
        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/"
        resp = api_client.get(url)
        assert resp.status_code == 200

    def test_update_api(self, api_client, pd, plugin, release, iam_policy_client, setup_bk_user):
        url = f"/api/bkplugins/{pd.identifier}/plugins/{plugin.id}/"
        resp = api_client.post(url)
        assert resp.status_code == 400
        # 已经下架的操作还可以操作
        assert resp.json()["detail"] != error_codes.PLUGIN_ARCHIVED.message


class TestSysApis:
    @pytest.mark.parametrize(
        'current_status, approve_result, stage_status',
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
        callback_data['current_status'] = current_status
        callback_data['approve_result'] = approve_result

        resp_data = api_client.post(callback_url, callback_data).json()

        assert resp_data['code'] == 0
        assert resp_data['result'] is True
        stage = release.all_stages.get(id=itsm_online_stage.id)
        assert stage.status == stage_status

    @pytest.mark.parametrize(
        'current_status, approve_result, plugin_status',
        [
            (ItsmTicketStatus.FINISHED.value, False, PluginStatus.APPROVAL_FAILED.value),
            (ItsmTicketStatus.TERMINATED.value, False, PluginStatus.APPROVAL_FAILED.value),
            (ItsmTicketStatus.REVOKED.value, True, PluginStatus.APPROVAL_FAILED.value),
        ],
    )
    def test_itsm_create_callback(self, api_client, pd, plugin, current_status, approve_result, plugin_status):
        callback_url = "/open/api/itsm/bkplugins/" + f"{pd.identifier}/plugins/{plugin.id}/"

        callback_data = CALLBACK_DATA
        callback_data['current_status'] = current_status
        callback_data['approve_result'] = approve_result
        resp_data = api_client.post(callback_url, callback_data).json()

        assert resp_data['code'] == 0
        assert resp_data['result'] is True
        plugin.refresh_from_db()
        assert plugin.status == plugin_status
