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
import json
from unittest import mock

import pytest
import requests

from paasng.pluginscenter.constants import PluginReleaseStatus
from paasng.pluginscenter.itsm_adaptor.utils import get_ticket_status, submit_online_approval_ticket

pytestmark = pytest.mark.django_db


@pytest.fixture
def set_itsm_to_current_stage(release, itsm_online_stage):
    release.current_stage = itsm_online_stage
    release.save(update_fields=["current_stage"])


@pytest.fixture
def mock_client_session():
    with mock.patch("bkapi_client_core.session.Session.request") as mocked_request:
        yield mocked_request


def test_execute_itsm_stage(
    mock_client_session, set_itsm_to_current_stage, online_approval_service, pd, plugin, release, bk_user
):
    """测试执行 itsm 阶段"""
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"data": {"sn": "sn1"}, "code": 0}'
    mock_client_session.return_value = response

    submit_online_approval_ticket(pd, plugin, release, bk_user.username)
    assert mock_client_session.called

    assert release.current_stage.status == PluginReleaseStatus.PENDING
    assert release.current_stage.itsm_detail.sn == "sn1"


def test_itsm_render(mock_client_session, set_itsm_to_current_stage):
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

    assert ticket_info['current_status_display'] == '被挂起'
    assert ticket_info['can_withdraw'] is True
