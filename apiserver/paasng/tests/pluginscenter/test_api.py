# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from unittest import mock

import pytest

from paasng.pluginscenter.constants import PluginReleaseStatus, PluginStatus
from paasng.pluginscenter.itsm_adaptor.constants import ItsmTicketStatus
from paasng.pluginscenter.views import PluginReleaseStageApiViewSet

pytestmark = pytest.mark.django_db


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
            "/sys/api/bkplugins/"
            + f"{pd.identifier}/plugins/{plugin.id}/releases/{release.id}/stages/{itsm_online_stage.id}/itsm/"
        )

        callback_data = CALLBACK_DATA
        callback_data['current_status'] = current_status
        callback_data['approve_result'] = approve_result

        with mock.patch.object(PluginReleaseStageApiViewSet, "_verify_itsm_token") as mocked_verify:
            mocked_verify.return_value = True
            resp_data = api_client.post(callback_url, callback_data).json()

            assert resp_data['code'] == 0
            assert resp_data['result'] is True
            stage = release.all_stages.get(id=itsm_online_stage.id)
            assert stage.status == stage_status

    @pytest.mark.parametrize(
        'current_status, approve_result, plugin_status',
        [
            (ItsmTicketStatus.FINISHED.value, True, PluginStatus.DEVELOPING.value),
            (ItsmTicketStatus.FINISHED.value, False, PluginStatus.APPROVAL_FAILED.value),
            (ItsmTicketStatus.TERMINATED.value, False, PluginStatus.APPROVAL_FAILED.value),
            (ItsmTicketStatus.REVOKED.value, True, PluginStatus.APPROVAL_FAILED.value),
        ],
    )
    def test_itsm_create_callback(self, api_client, pd, plugin, current_status, approve_result, plugin_status):
        callback_url = "/sys/api/bkplugins/" + f"{pd.identifier}/plugins/{plugin.id}/itsm/"

        callback_data = CALLBACK_DATA
        callback_data['current_status'] = current_status
        callback_data['approve_result'] = approve_result

        with mock.patch.object(PluginReleaseStageApiViewSet, "_verify_itsm_token") as mocked_verify, mock.patch(
            "paasng.pluginscenter.shim.init_plugin_in_view"
        ):
            mocked_verify.return_value = True
            resp_data = api_client.post(callback_url, callback_data).json()

            assert resp_data['code'] == 0
            assert resp_data['result'] is True
            plugin.refresh_from_db()
            assert plugin.status == plugin_status
