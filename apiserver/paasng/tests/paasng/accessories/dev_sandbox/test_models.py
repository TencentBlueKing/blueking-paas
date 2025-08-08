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

import json

import pytest

from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.sourcectl.models import VersionInfo

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def dev_sandbox(bk_cnative_app, bk_module, bk_user) -> DevSandbox:
    version_info = VersionInfo(revision="...", version_name="master", version_type="branch")
    return DevSandbox.objects.create(
        module=bk_module,
        owner=bk_user,
        env_vars={},
        version_info=version_info,
        enable_code_editor=True,
        enabled_addons_services=[],
    )


class TestDevSandboxModelMethods:
    def test_list_env_vars_empty(self, dev_sandbox):
        """测试获取空环境变量列表"""
        assert dev_sandbox.list_env_vars() == []

    def test_list_env_vars_with_data(self, dev_sandbox):
        """测试获取有数据的环境变量列表"""
        env_vars = [
            {"key": "DB_HOST", "value": "127.0.0.1", "source": "custom"},
            {"key": "DB_PORT", "value": "3306", "source": "custom"},
        ]
        dev_sandbox.env_vars = json.dumps(env_vars)
        dev_sandbox.save()

        assert dev_sandbox.list_env_vars() == env_vars

    def test_upsert_env_vars_new(self, dev_sandbox):
        """测试新增环境变量"""
        # 初始环境变量为空
        assert dev_sandbox.list_env_vars() == []

        # 新增环境变量
        dev_sandbox.upsert_env_var(key="NEW_VAR", value="new_value")

        result = dev_sandbox.list_env_vars()
        assert result == [{"key": "NEW_VAR", "value": "new_value", "source": "custom"}]

    def test_upsert_env_vars_update(self, dev_sandbox):
        """测试更新环境变量"""
        # 设置初始环境变量
        initial_vars = [
            {"key": "EXISTING_VAR", "value": "old_value", "source": "custom"},
            {"key": "ANOTHER_VAR", "value": "value", "source": "custom"},
        ]
        dev_sandbox.env_vars = json.dumps(initial_vars)
        dev_sandbox.save()

        # 更新环境变量
        dev_sandbox.upsert_env_var(key="EXISTING_VAR", value="updated_value")

        result = dev_sandbox.list_env_vars()
        assert len(result) == 2
        assert {"key": "EXISTING_VAR", "value": "updated_value", "source": "custom"} in result
        assert {"key": "ANOTHER_VAR", "value": "value", "source": "custom"} in result

    def test_delete_env_vars_existing(self, dev_sandbox):
        """测试删除存在的环境变量"""
        # 设置初始环境变量
        initial_vars = [
            {"key": "VAR1", "value": "value1", "source": "custom"},
            {"key": "VAR2", "value": "value2", "source": "custom"},
            {"key": "VAR3", "value": "value3", "source": "custom"},
        ]
        dev_sandbox.env_vars = json.dumps(initial_vars)
        dev_sandbox.save()

        # 删除环境变量
        dev_sandbox.delete_env_var(key="VAR2")

        result = dev_sandbox.list_env_vars()
        assert len(result) == 2
        assert {"key": "VAR1", "value": "value1", "source": "custom"} in result
        assert {"key": "VAR3", "value": "value3", "source": "custom"} in result

    def test_delete_env_vars_non_existing(self, dev_sandbox):
        """测试删除不存在的环境变量"""
        # 设置初始环境变量
        initial_vars = [
            {"key": "VAR1", "value": "value1", "source": "custom"},
            {"key": "VAR2", "value": "value2", "source": "custom"},
        ]
        dev_sandbox.env_vars = json.dumps(initial_vars)
        dev_sandbox.save()

        # 删除不存在的环境变量
        dev_sandbox.delete_env_var(key="NON_EXISTING")

        result = dev_sandbox.list_env_vars()
        assert result == initial_vars

    def test_upsert_env_vars_with_source(self, dev_sandbox):
        """测试新增环境变量时覆盖来源为 custom"""
        # 设置初始环境变量（包含不同来源）
        initial_vars = [
            {"key": "VAR1", "value": "value1", "source": "stag"},
            {"key": "VAR2", "value": "value2", "source": "custom"},
        ]
        dev_sandbox.env_vars = json.dumps(initial_vars)
        dev_sandbox.save()

        # 更新环境变量（覆盖为 custom）
        dev_sandbox.upsert_env_var(key="VAR1", value="updated_value")
        dev_sandbox.upsert_env_var(key="VAR2", value="updated_value")

        result = dev_sandbox.list_env_vars()
        assert len(result) == 2
        assert {"key": "VAR1", "value": "updated_value", "source": "custom"} in result
        assert {"key": "VAR2", "value": "updated_value", "source": "custom"} in result

    def test_delete_env_vars_empty(self, dev_sandbox):
        """测试在空环境变量上删除"""
        # 初始环境变量为空
        assert dev_sandbox.list_env_vars() == []

        # 删除环境变量
        dev_sandbox.delete_env_var(key="ANY_KEY")

        assert dev_sandbox.list_env_vars() == []

    def test_upsert_env_vars_multiple(self, dev_sandbox):
        """测试多次更新环境变量"""
        # 初始环境变量为空
        assert dev_sandbox.list_env_vars() == []

        # 多次更新环境变量
        dev_sandbox.upsert_env_var(key="VAR1", value="value1")
        dev_sandbox.upsert_env_var(key="VAR2", value="value2")
        dev_sandbox.upsert_env_var(key="VAR1", value="updated_value")

        result = dev_sandbox.list_env_vars()
        assert len(result) == 2
        assert {"key": "VAR1", "value": "updated_value", "source": "custom"} in result
        assert {"key": "VAR2", "value": "value2", "source": "custom"} in result
