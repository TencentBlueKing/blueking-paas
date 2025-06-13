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

from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware
from django_dynamic_fixture import G
from rest_framework import status

from paasng.misc.audit.models import AdminOperationRecord
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db


class TestAuditBaseTestCase:
    """审计测试基类，提供通用的测试数据和方法"""

    @pytest.fixture(autouse=True)
    def create_audit_records(self, bk_app, bk_user):
        """创建审计测试记录"""
        # 设置基础时间
        base_time = make_aware(datetime(2024, 1, 1, 0, 0, 0))

        # 创建另外一个用户
        another_user = create_user(username="another_user")

        # 定义测试记录配置
        records_config = [
            # (app_code, target, operation, result_code, user, hours_offset)
            ## 应用操作记录
            (bk_app.code, "app", "create", 0, bk_user, 0),
            (bk_app.code, "process", "start", 0, bk_user, 1),
            (bk_app.code, "app", "delete", -1, another_user, 22),
            (bk_app.code, "process", "deploy", 0, another_user, 23),
            (bk_app.code, "app", "modify", 1, bk_user, 23.5),
            ## 平台操作记录（app_code=None）
            (None, "app", "create", 0, bk_user, 0),
            (None, "process", "start", 0, bk_user, 1),
            (None, "app", "delete", -1, another_user, 22),
            (None, "process", "deploy", 0, another_user, 23),
            (None, "app", "modify", 1, bk_user, 23.5),
        ]

        # 批量创建记录
        for app_code, target, operation, result_code, user, hours_offset in records_config:
            G(
                AdminOperationRecord,
                app_code=app_code,
                target=target,
                operation=operation,
                result_code=result_code,
                user=user.pk,
                created=base_time + timedelta(hours=hours_offset),
            )


class TestApplicationOperateAuditViewSet(TestAuditBaseTestCase):
    """测试应用操作审计相关接口"""

    @pytest.mark.parametrize(
        ("filter_key", "expected_count"),
        [
            ({}, 5),  # 无过滤条件，应该返回所有记录
            ({"target": "app"}, 3),  # 仅过滤应用操作
            ({"operation": "deploy"}, 1),  # 仅过滤部署操作
            ({"status": -1}, 1),  # 仅过滤失败状态
            ({"operator": "another_user"}, 2),  # 仅过滤 another_user 的操作
            ({"start_time": "2024-01-01 22:00:00"}, 3),  # 从某个时间点开始
            ({"end_time": "2024-01-01 21:00:00"}, 2),  # 到某个时间点结束
            # 组合过滤
            ({"target": "app", "operation": "create"}, 1),  # 应用新建操作
            ({"status": 0, "operator": "another_user"}, 1),  # another_user 成功操作
            ({"start_time": "2024-01-01 01:00:00", "end_time": "2024-01-02 00:00:00"}, 4),  # 时间范围过滤
        ],
    )
    def test_filter_list(self, plat_mgt_api_client, filter_key, expected_count):
        """测试应用操作审计列表的过滤功能"""

        url = reverse("plat_mgt.audit.applications.list")
        resp = plat_mgt_api_client.get(url, filter_key)
        assert resp.status_code == status.HTTP_200_OK

        assert resp.data["count"] == expected_count

    def test_retrieve(self, plat_mgt_api_client, bk_app):
        record = AdminOperationRecord.objects.filter(app_code=bk_app.code).first()
        url = reverse(
            "plat_mgt.audit.applications.retrieve",
            kwargs={"uuid": record.uuid},
        )
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "target" in resp.data


class TestPlatformOperationAuditViewSet(TestAuditBaseTestCase):
    """测试平台操作审计相关接口"""

    @pytest.mark.parametrize(
        ("filter_key", "expected_count"),
        [
            ({}, 5),  # 无过滤条件，应该返回所有记录
            ({"target": "app"}, 3),  # 仅过滤应用操作
            ({"operation": "deploy"}, 1),  # 仅过滤部署操作
            ({"status": 0}, 3),  # 仅过滤成功状态
            ({"operator": "another_user"}, 2),  # 仅过滤 another_user 的操作
            ({"start_time": "2024-01-01 22:00:00"}, 3),  # 从某个时间点开始
            ({"end_time": "2024-01-01 21:00:00"}, 2),  # 到某个时间点结束
            # 组合过滤
            ({"target": "app", "operation": "create"}, 1),  # 应用新建操作
            ({"status": 0, "operator": "another_user"}, 1),  # another_user 成功操作
            ({"start_time": "2024-01-01 01:00:00", "end_time": "2024-01-02 00:00:00"}, 4),  # 时间范围过滤
        ],
    )
    def test_filter_list(self, plat_mgt_api_client, filter_key, expected_count):
        url = reverse("plat_mgt.audit.platform.list")
        resp = plat_mgt_api_client.get(url, filter_key)
        assert resp.status_code == status.HTTP_200_OK
        print(resp.data)
        assert resp.data["count"] == expected_count

    def test_retrieve(self, plat_mgt_api_client):
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
