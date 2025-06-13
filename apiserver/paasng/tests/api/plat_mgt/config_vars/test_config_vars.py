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

from paasng.platform.engine.models.config_var import BuiltinConfigVar

pytestmark = pytest.mark.django_db


class TestBuiltinConfigVarViewSet:
    """测试内建环境变量视图集"""

    @pytest.fixture(autouse=True)
    def create_builtin_config_var(self, bk_user):
        """创建一个内建环境变量"""
        config_var = BuiltinConfigVar.objects.create(
            key="BUILTIN_TEST_VAR",
            value="test_value",
            description="Test variable",
            operator=bk_user,
        )
        return config_var

    def test_list(self, plat_mgt_api_client, create_builtin_config_var):
        """测试获取内建环境变量列表"""
        url = reverse("plat_mgt.builtin_config_vars.bulk")
        resp = plat_mgt_api_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_create(self, plat_mgt_api_client, plat_manager_user):
        """测试创建内建环境变量"""
        data = {
            "key": "TEST_VAR",
            "value": "test_value",
            "description": "Test variable",
        }
        url = reverse("plat_mgt.builtin_config_vars.bulk")
        resp = plat_mgt_api_client.post(url, data=data)
        assert resp.status_code == 201

        # 确认创建的内建环境变量
        created_var = BuiltinConfigVar.objects.get(key=data["key"])
        assert created_var.value == data["value"]
        assert created_var.operator == plat_manager_user.pk

    def test_update(self, plat_mgt_api_client, create_builtin_config_var):
        """测试更新内建环境变量"""
        data = {
            "value": "updated_value",
            "description": "Updated variable",
        }
        url = reverse("plat_mgt.builtin_config_vars.detail", kwargs={"pk": create_builtin_config_var.pk})

        resp = plat_mgt_api_client.put(url, data=data)
        assert resp.status_code == 204

        # 确认更新的内建环境变量
        updated_var = BuiltinConfigVar.objects.get(pk=create_builtin_config_var.pk)
        assert updated_var.value == data["value"]

    def test_delete(self, plat_mgt_api_client, create_builtin_config_var):
        """测试删除内建环境变量"""
        url = reverse("plat_mgt.builtin_config_vars.detail", kwargs={"pk": create_builtin_config_var.pk})
        resp = plat_mgt_api_client.delete(url)
        assert resp.status_code == 204

        # 确认删除
        with pytest.raises(BuiltinConfigVar.DoesNotExist):
            BuiltinConfigVar.objects.get(pk=create_builtin_config_var.pk)
