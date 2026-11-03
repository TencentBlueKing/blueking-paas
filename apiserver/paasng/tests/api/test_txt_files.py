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

from unittest import mock

import pytest

from paas_wl.workloads.networking.ingress.models import TxtFile

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def url(bk_cnative_app, bk_module):
    return f"/api/bkapps/applications/{bk_cnative_app.code}/modules/{bk_module.name}/envs/stag/txt_files/"


SYNC_PATH = "paas_wl.workloads.networking.ingress.txt_files.views.sync_txt_file_ingresses"


@mock.patch(SYNC_PATH, return_value=["foo.example.com"])
def test_create_and_list(mocked_sync, api_client, bk_user, bk_stag_env, url):
    resp = api_client.post(url, data={"path": "/verify.txt", "content": "abc"})
    assert resp.status_code == 201
    assert resp.data["operator"] == bk_user.username
    assert mocked_sync.called

    resp = api_client.get(url)
    assert [f["path"] for f in resp.data["files"]] == ["/verify.txt"]


@pytest.mark.parametrize(
    ("sync_result", "error_code"),
    [
        ({"side_effect": RuntimeError("boom")}, "SYNC_TXT_FILE_FAILED"),
        # The environment isn't deployed
        ({"return_value": []}, "TXT_FILE_NO_SERVED_HOST"),
    ],
)
def test_rollback_when_sync_failed(api_client, bk_stag_env, url, sync_result, error_code):
    with mock.patch(SYNC_PATH, **sync_result):
        resp = api_client.post(url, data={"path": "/verify.txt", "content": "abc"})
    assert resp.status_code == 400
    assert resp.data["code"] == error_code
    assert not TxtFile.objects.filter(environment_id=bk_stag_env.id).exists()
