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

import pytest


@pytest.fixture(autouse=True)
def _set_login_full(settings):
    settings.LOGIN_FULL = "https://login.example.com/"


async def test_anonymous_user_info(aanonymous_api_client):
    response = await aanonymous_api_client.get("/api/accounts/userinfo/")

    assert response.status_code == 401
    assert response.json() == {
        "authenticated": False,
        "login_url": "https://login.example.com/",
    }


async def test_authenticated_user_info(aapi_client, bk_user):
    response = await aapi_client.get("/api/accounts/userinfo/")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "username": bk_user.username,
        "display_name": bk_user.display_name,
        "tenant_id": bk_user.tenant_id,
    }
