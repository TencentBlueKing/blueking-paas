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
import pytest

from paasng.misc.audit.service import add_app_audit_record
from tests.conftest import create_app, generate_random_string
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db


class TestAuditAPI:
    def test_latest_apps(self, api_client, bk_user, bk_app):
        """最近操作的应用列表"""
        add_app_audit_record(
            app_code=bk_app.code, action_id="", user=bk_user, operation="enable", target="addon", attribute="mysql"
        )
        add_app_audit_record(
            app_code=bk_app.code,
            action_id="",
            user=bk_user,
            operation="disable",
            target="addon",
            attribute="mysql",
        )

        url = "/api/bkapps/applications/lists/latest/"
        resp = api_client.get(url)
        assert resp.status_code == 200
        data = resp.json()["results"]
        # 仅返回应用最新一条操作记录
        assert len(data) == 1
        assert data[0]["operation"] == "disable"
        assert data[0]["application"]["code"] == bk_app.code

    def test_latest_apps_filter_by_operator(self, api_client, bk_user, bk_app):
        """最近操作的应用列表"""
        add_app_audit_record(
            app_code=bk_app.code, action_id="", user=bk_user, operation="enable", target="addon", attribute="mysql"
        )

        # 创建另一条操作记录，应用属于 bk_user, 但操作人是 test_user
        bk_app2 = create_app(owner_username=bk_user.username)
        test_user = create_user(generate_random_string(6))
        add_app_audit_record(
            app_code=bk_app2.code,
            action_id="",
            user=test_user,
            operation="disable",
            target="addon",
            attribute="mysql",
        )

        url = "/api/bkapps/applications/lists/latest/"
        params = {"limit": 5, "operator": bk_user.username}
        resp = api_client.get(url, params)
        assert resp.status_code == 200
        data = resp.json()["results"]
        # 仅返回操作人的应用最新一条操作记录
        assert len(data) == 1
        assert data[0]["operation"] == "enable"
        assert data[0]["application"]["code"] == bk_app.code
        assert data[0]["operator"] == bk_user.username
