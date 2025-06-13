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

from paasng.misc.audit.constants import OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.models import AdminOperationRecord
from tests.utils.auth import create_user

pytestmark = pytest.mark.django_db


class TestApplicationOperateAuditViewSet:
    """测试应用操作审计相关接口"""

    @pytest.fixture(autouse=True)
    def create_app_op_record(self, bk_app, bk_user):
        """创建一些应用操作日志"""
        # 设置基础时间
        base_time = make_aware(datetime(2024, 1, 1, 0, 0, 0))

        # 创建另外一个用户
        another_user = create_user(username="another_user")

        # 记录1: 应用操作 - 新建 - 成功 - bk_user - 2024-01-01 00:00:00
        G(
            AdminOperationRecord,
            app_code=bk_app.code,
            target=OperationTarget.APP.value,
            operation=OperationEnum.CREATE.value,
            result_code=ResultCode.SUCCESS.value,
            user=bk_user.pk,
            created=base_time,
        )
        # 记录2: 进程操作 - 启动 - 成功 - bk_user - 2024-01-01 01:00:00
        G(
            AdminOperationRecord,
            app_code=bk_app.code,
            target=OperationTarget.PROCESS.value,
            operation=OperationEnum.START.value,
            result_code=ResultCode.SUCCESS.value,
            user=bk_user.pk,
            created=base_time + timedelta(hours=1),
        )
        # 记录3: 应用操作 - 删除 - 失败 - another_user - 2024-01-01 22:00:00
        G(
            AdminOperationRecord,
            app_code=bk_app.code,
            target=OperationTarget.APP.value,
            operation=OperationEnum.DELETE.value,
            result_code=ResultCode.FAILURE.value,
            user=another_user.pk,
            created=base_time + timedelta(hours=22),
        )
        # 记录4: 进程操作 - 部署 - 成功 - another_user - 2024-01-01 23:00:00
        G(
            AdminOperationRecord,
            app_code=bk_app.code,
            target=OperationTarget.PROCESS.value,
            operation=OperationEnum.DEPLOY.value,
            result_code=ResultCode.SUCCESS.value,
            user=another_user.pk,
            created=base_time + timedelta(hours=23),
        )
        # 记录5: 应用操作 - 修改 - 执行中 - bk_user - 2024-01-01 23:30:00
        G(
            AdminOperationRecord,
            app_code=bk_app.code,
            target=OperationTarget.APP.value,
            operation=OperationEnum.MODIFY.value,
            result_code=ResultCode.ONGOING.value,
            user=bk_user.pk,
            created=base_time + timedelta(hours=23, minutes=30),
        )

    @pytest.mark.parametrize(
        ("filter_key", "expected_count"),
        [
            ({}, 5),  # 无过滤条件，应该返回所有记录
            ({"target": OperationTarget.APP.value}, 3),  # 仅过滤应用操作
            ({"operation": OperationEnum.DEPLOY.value}, 1),  # 仅过滤部署操作
            ({"status": ResultCode.FAILURE.value}, 1),  # 仅过滤失败状态
            ({"operator": "another_user"}, 2),  # 仅过滤 another_user 的操作
            ({"start_time": "2024-01-01 22:00:00"}, 3),  # 从某个时间点开始
            ({"end_time": "2024-01-01 21:00:00"}, 2),  # 到某个时间点结束
            # 组合过滤
            ({"target": OperationTarget.APP.value, "operation": OperationEnum.CREATE.value}, 1),  # 应用新建操作
            ({"status": ResultCode.SUCCESS.value, "operator": "another_user"}, 2),  # another_user 成功操作
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


class TestPlatformOperationAuditViewSet:
    """测试平台操作审计相关接口"""

    @pytest.fixture(autouse=True)
    def create_platform_op_record(self, bk_app, bk_user):
        # 创建一些平台操作审计日志
        # 设置基础时间
        base_time = make_aware(datetime(2024, 1, 1, 0, 0, 0))

        # 创建另外一个用户
        another_user = create_user(username="another_user")

        # 记录1: 应用操作 - 新建 - 成功 - bk_user - 2024-01-01 00:00:00
        G(
            AdminOperationRecord,
            app_code=None,
            target=OperationTarget.APP.value,
            operation=OperationEnum.CREATE.value,
            result_code=ResultCode.SUCCESS.value,
            user=bk_user.pk,
            created=base_time,
        )
        # 记录2: 进程操作 - 启动 - 成功 - bk_user - 2024-01-01 01:00:00
        G(
            AdminOperationRecord,
            app_code=None,
            target=OperationTarget.PROCESS.value,
            operation=OperationEnum.START.value,
            result_code=ResultCode.SUCCESS.value,
            user=bk_user.pk,
            created=base_time + timedelta(hours=1),
        )
        # 记录3: 应用操作 - 删除 - 失败 - another_user - 2024-01-01 22:00:00
        G(
            AdminOperationRecord,
            app_code=None,
            target=OperationTarget.APP.value,
            operation=OperationEnum.DELETE.value,
            result_code=ResultCode.FAILURE.value,
            user=another_user.pk,
            created=base_time + timedelta(hours=22),
        )
        # 记录4: 进程操作 - 部署 - 成功 - another_user - 2024-01-01 23:00:00
        G(
            AdminOperationRecord,
            app_code=None,
            target=OperationTarget.PROCESS.value,
            operation=OperationEnum.DEPLOY.value,
            result_code=ResultCode.SUCCESS.value,
            user=another_user.pk,
            created=base_time + timedelta(hours=23),
        )
        # 记录5: 应用操作 - 修改 - 执行中 - bk_user - 2024-01-01 23:30:00
        G(
            AdminOperationRecord,
            app_code=None,
            target=OperationTarget.APP.value,
            operation=OperationEnum.MODIFY.value,
            result_code=ResultCode.ONGOING.value,
            user=bk_user.pk,
            created=base_time + timedelta(hours=23, minutes=30),
        )

    @pytest.mark.parametrize(
        ("filter_key", "expected_count"),
        [
            ({}, 5),  # 无过滤条件，应该返回所有记录
            ({"target": OperationTarget.APP.value}, 3),  # 仅过滤应用操作
            ({"operation": OperationEnum.DEPLOY.value}, 1),  # 仅过滤部署操作
            ({"status": ResultCode.SUCCESS.value}, 3),  # 仅过滤成功状态
            ({"operator": "another_user"}, 2),  # 仅过滤 another_user 的操作
            ({"start_time": "2024-01-01 22:00:00"}, 3),  # 从某个时间点开始
            ({"end_time": "2024-01-01 21:00:00"}, 2),  # 到某个时间点结束
            # 组合过滤
            ({"target": OperationTarget.APP.value, "operation": OperationEnum.CREATE.value}, 1),  # 应用新建操作
            ({"status": ResultCode.SUCCESS.value, "operator": "another_user"}, 1),  # another_user 成功操作
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
