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

from paasng.platform.engine.models.config_var import BuiltinConfigVar

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.usefixtures("_with_wl_apps")
class TestConfigVarBuiltinViewSet:
    def test_get_builtin_envs(self, api_client, bk_app, bk_module):
        """测试返回内置环境变量"""

        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/builtin/"
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert isinstance(data["stag"], list)
        assert isinstance(data["prod"], list)

    def test_get_builtin_envs_with_custom_vars(self, api_client, bk_app, bk_module):
        """测试平台管理自定义内置环境变量覆盖原有内置环境变量"""
        # 测试 BKPAAS_MULTI_TENANT_MODE, 原有内置环境值为 False
        # 因为 BKPAAS_ 前缀默认添加, 在数据库中不存储该前缀
        BuiltinConfigVar.objects.create(key="MULTI_TENANT_MODE", value="value1", description="自定义内置变量1")
        BuiltinConfigVar.objects.create(key="CUSTOM_VAR_2", value="value2", description="自定义内置变量2")

        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/builtin/"
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()

        for env in ["stag", "prod"]:
            env_vars = data[env]
            mt_var = next(item for item in env_vars if item["key"] == "BKPAAS_MULTI_TENANT_MODE")
            assert mt_var is not None
            assert mt_var["value"] == "value1"


@pytest.mark.usefixtures("_with_wl_apps")
class TestConflictedConfigVarsViewSet:
    def test_list_with_override_flag(self, api_client, bk_app, bk_module):
        """测试获取环境变量及其可覆盖性"""

        url = f"/api/bkapps/applications/{bk_app.code}/modules/{bk_module.name}/config_vars/conflict_info/"
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0
