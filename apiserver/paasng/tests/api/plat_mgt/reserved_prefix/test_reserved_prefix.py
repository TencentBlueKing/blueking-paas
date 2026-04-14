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

from paasng.platform.applications.models import ReservedPrefixAuthCode

pytestmark = pytest.mark.django_db


class TestAuthCodeManageViewSet:
    """保留前缀授权码管理 API 测试"""

    @pytest.fixture(autouse=True)
    def _setup_records(self):
        """创建测试记录"""
        ReservedPrefixAuthCode.objects.create(
            auth_code="TCODE001",
            app_code="bk-test01",
            is_used=False,
        )
        ReservedPrefixAuthCode.objects.create(
            auth_code="TCODE002",
            app_code="bk-test02",
            is_used=True,
        )

    @pytest.mark.parametrize(
        ("query_params", "expected_count"),
        [
            ({}, 2),  # 不传参数，返回所有记录
            ({"search": "bk-test01"}, 1),  # 根据 app_code 过滤
            ({"search": "TCODE"}, 2),  # 根据 auth_code 过滤
        ],
    )
    def test_list(self, plat_mgt_api_client, query_params, expected_count):
        """测试获取授权码列表接口"""
        url = reverse("plat_mgt.reserved_prefix.list")
        response = plat_mgt_api_client.get(url, data=query_params)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == expected_count

    @pytest.mark.parametrize(
        ("data", "expected_status"),
        [
            ({"app_code": "bk-new-app"}, status.HTTP_201_CREATED),  # 正常创建
            ({"app_code": "bk-test01"}, status.HTTP_400_BAD_REQUEST),  # app_code 已存在
            ({}, status.HTTP_400_BAD_REQUEST),  # 缺少 app_code
        ],
    )
    def test_create(self, plat_mgt_api_client, data, expected_status):
        """测试生成授权码接口"""
        url = reverse("plat_mgt.reserved_prefix.list")
        response = plat_mgt_api_client.post(url, data=data)

        assert response.status_code == expected_status
        if expected_status == status.HTTP_201_CREATED:
            assert "auth_code" in response.data
            assert len(response.data["auth_code"]) == 8

    @pytest.mark.parametrize(
        ("used_record", "expected_status"),
        [
            (False, status.HTTP_204_NO_CONTENT),  # 删除未使用的授权码
            (True, status.HTTP_400_BAD_REQUEST),  # 删除已使用的授权码
        ],
    )
    def test_destroy(self, plat_mgt_api_client, used_record, expected_status):
        """测试删除授权码接口"""
        auth_code = ReservedPrefixAuthCode.objects.create(
            app_code="bk-delete-test",
            auth_code="DELCODE1",
            is_used=used_record,
        )
        url = reverse("plat_mgt.reserved_prefix.destroy", kwargs={"id": auth_code.id})
        response = plat_mgt_api_client.delete(url)

        assert response.status_code == expected_status

    def test_destroy_nonexistent(self, plat_mgt_api_client):
        """测试删除不存在的授权码"""
        url = reverse("plat_mgt.reserved_prefix.destroy", kwargs={"id": 9999})
        response = plat_mgt_api_client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
