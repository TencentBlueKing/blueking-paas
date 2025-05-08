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


from dataclasses import dataclass
from unittest import mock

import pytest

from tests.paasng.platform.engine.setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db


# Simulates colored logs using ANSI escape codes
ansi_log = "\u001b[38;2;255;156;1m\u001b[1mDeployment successful\u001b[0m\n\u001b[1GProgress: 100%\u001b[0m"
plain_log = "Deployment successful\nProgress: 100%"


@pytest.fixture
def prepare_data(bk_app, bk_module):
    deployment = create_fake_deployment(bk_module)
    return bk_app, bk_module, deployment


def fake_get_all_logs(deployment):
    return ansi_log


def fake_get_failure_hint(deployment):
    @dataclass
    class Hint:
        reason: str = "fake reason"
        solution: str = "fake solution"

    return Hint()


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", plain_log),
        ("?include_ansi_codes=true", ansi_log),
        ("?include_ansi_codes=false", plain_log),
    ],
)
def test_get_deployment_result(api_client, prepare_data, query, expected):
    bk_app, bk_module, deployment = prepare_data
    base_url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/deployments/{deployment.id}/result/"
    url = base_url + query
    with (
        mock.patch("paasng.platform.engine.views.deploy.get_all_logs", fake_get_all_logs),
        mock.patch("paasng.platform.engine.views.deploy.get_failure_hint", fake_get_failure_hint),
    ):
        rsp = api_client.get(url)
        assert rsp.status_code == 200
        assert rsp.json().get("logs") == expected
