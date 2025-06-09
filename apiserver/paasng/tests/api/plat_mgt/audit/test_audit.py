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
from django.urls import reverse
from rest_framework import status

from paasng.misc.audit.models import AdminOperationRecord

pytestmark = pytest.mark.django_db


class TestApplicationOperateAuditViewSet:
    """测试应用操作审计相关接口"""

    @pytest.fixture(autouse=True)
    def create_app_op_record(self, bk_app, bk_user):
        # 创建应用操作审计日志
        AdminOperationRecord.objects.create(
            app_code=bk_app.code,
            user=bk_user.pk,
            operation="modify_basic_info",
            target="app",
            result_code=0,
        )

    def test_list(self, plat_mgt_api_client):
        url = reverse("plat_mgt.audit.applications.list")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) > 0

    def test_retrieve(self, plat_mgt_api_client, bk_app):
        record = AdminOperationRecord.objects.filter(app_code=bk_app.code).first()
        url = reverse(
            "plat_mgt.audit.applications.retrieve",
            kwargs={"uuid": record.uuid},
        )
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "target" in resp.data


class TestPlatformOperationAuditViewSet:
    """测试平台操作审计相关接口"""

    @pytest.fixture(autouse=True)
    def create_admin_op_record(self, bk_app, bk_user):
        # 创建一个平台操作审计日志
        AdminOperationRecord.objects.create(
            user=bk_user.pk,
            operation="start",
            target="process",
            attribute="web",
            result_code=0,
        )

    def test_list(self, plat_mgt_api_client):
        url = reverse("plat_mgt.audit.platform.list")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) > 0

    def test_retrieve(self, plat_mgt_api_client, bk_app):
        record = AdminOperationRecord.objects.filter(app_code=None).first()
        url = reverse(
            "plat_mgt.audit.platform.retrieve",
            kwargs={"uuid": record.uuid},
        )
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "target" in resp.data


class TestAuditFilterOptionsViewSet:
    """测试审计过滤选项 API"""

    def test_list(self, plat_mgt_api_client):
        url = reverse("plat_mgt.audit.filter_options")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, dict)
        assert len(data["target"]) > 0
        assert len(data["operation"]) > 0
        assert len(data["status"]) > 0
