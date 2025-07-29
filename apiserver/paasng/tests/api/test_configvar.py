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


class TestConfigVarBuiltinViewSet:
    def test_get_custom_builtin_envs_single_vars(self, api_client, bk_app):
        """测试返回单个平台内置环境变量"""
        BuiltinConfigVar.objects.create(key="CUSTOM_VAR", value="value", description="自定义内置变量")

        url = reverse("api.config_vars.builtin.custom", kwargs={"code": bk_app.code})
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert "BKPAAS_CUSTOM_VAR" in data
        assert data["BKPAAS_CUSTOM_VAR"]["value"] == "value"
        assert data["BKPAAS_CUSTOM_VAR"]["description"] == "自定义内置变量"

    def test_get_custom_builtin_envs_multiple_vars(self, api_client, bk_app):
        """测试返回多个平台内置环境变量"""
        BuiltinConfigVar.objects.create(key="CUSTOM_VAR_1", value="value1", description="自定义内置变量1")
        BuiltinConfigVar.objects.create(key="CUSTOM_VAR_2", value="value2", description="自定义内置变量2")
        BuiltinConfigVar.objects.create(key="CUSTOM_VAR_3", value="value3", description="自定义内置变量3")

        url = reverse("api.config_vars.builtin.custom", kwargs={"code": bk_app.code})
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        assert "BKPAAS_CUSTOM_VAR_1" in data
        assert data["BKPAAS_CUSTOM_VAR_1"]["value"] == "value1"
        assert data["BKPAAS_CUSTOM_VAR_1"]["description"] == "自定义内置变量1"
        assert "BKPAAS_CUSTOM_VAR_2" in data
        assert data["BKPAAS_CUSTOM_VAR_2"]["value"] == "value2"
        assert data["BKPAAS_CUSTOM_VAR_2"]["description"] == "自定义内置变量2"
        assert "BKPAAS_CUSTOM_VAR_3" in data
        assert data["BKPAAS_CUSTOM_VAR_3"]["value"] == "value3"
        assert data["BKPAAS_CUSTOM_VAR_3"]["description"] == "自定义内置变量3"

    def test_get_custom_builtin_envs_with_no_data(self, api_client, bk_app):
        """测试没有平台内置环境变量时的返回结果"""
        BuiltinConfigVar.objects.all().delete()

        url = reverse("api.config_vars.builtin.custom", kwargs={"code": bk_app.code})
        response = api_client.get(url)

        assert response.status_code == 200
        assert response.json() == {}
