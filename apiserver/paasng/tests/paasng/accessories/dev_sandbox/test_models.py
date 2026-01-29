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
from typing import Dict, List, cast

import pytest

from paas_wl.bk_app.dev_sandbox.entities import DevSandboxEnvVarList
from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.sourcectl.models import VersionInfo

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def _env_vars_to_dicts(env_vars):
    return [env_var.to_dict() for env_var in env_vars]


def _env_vars_with_sensitive(env_vars: List[Dict[str, str]]):
    return [{**cast(Dict[str, object], env_var), "is_sensitive": False} for env_var in env_vars]


@pytest.fixture()
def dev_sandbox(bk_cnative_app, bk_module, bk_user) -> DevSandbox:
    version_info = VersionInfo(revision="...", version_name="master", version_type="branch")
    return DevSandbox.objects.create(
        module=bk_module,
        owner=bk_user,
        env_vars=DevSandboxEnvVarList([]),
        version_info=version_info,
        enable_code_editor=True,
        enabled_addons_services=[],
    )


class TestDevSandboxModelMethods:
    def test_list_env_vars_empty(self, dev_sandbox):
        """测试获取空环境变量列表"""
        assert list(dev_sandbox.list_env_vars()) == []

    def test_list_env_vars_with_data(self, dev_sandbox):
        """测试获取有数据的环境变量列表"""
        env_vars = [
            {"key": "DB_HOST", "value": "127.0.0.1", "source": "custom"},
            {"key": "DB_PORT", "value": "3306", "source": "custom"},
        ]
        dev_sandbox.env_vars = json.dumps(env_vars)
        dev_sandbox.save()

        expected = _env_vars_with_sensitive(env_vars)
        assert _env_vars_to_dicts(dev_sandbox.list_env_vars()) == expected

    def test_upsert_env_vars_new(self, dev_sandbox):
        """测试新增环境变量"""
        # 初始环境变量为空
        assert list(dev_sandbox.list_env_vars()) == []

        # 新增环境变量
        dev_sandbox.upsert_env_var(key="NEW_VAR", value="new_value")

        result = dev_sandbox.list_env_vars()
        assert result.map["NEW_VAR"].value == "new_value"
        assert result.map["NEW_VAR"].source == "custom"
        assert result.map["NEW_VAR"].is_sensitive is False

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
        assert result.map["EXISTING_VAR"].value == "updated_value"
        assert result.map["EXISTING_VAR"].source == "custom"
        assert result.map["ANOTHER_VAR"].value == "value"
        assert result.map["ANOTHER_VAR"].source == "custom"

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
        assert result.kv_map == {"VAR1": "value1", "VAR3": "value3"}

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
        expected = _env_vars_with_sensitive(initial_vars)
        assert _env_vars_to_dicts(result) == expected

    def test_upsert_env_vars_with_source(self, dev_sandbox):
        """测试更新环境变量时保留来源"""
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
        assert result.map["VAR1"].value == "updated_value"
        assert result.map["VAR1"].source == "stag"
        assert result.map["VAR2"].value == "updated_value"
        assert result.map["VAR2"].source == "custom"

    def test_delete_env_vars_empty(self, dev_sandbox):
        """测试在空环境变量上删除"""
        # 初始环境变量为空
        assert list(dev_sandbox.list_env_vars()) == []

        # 删除环境变量
        dev_sandbox.delete_env_var(key="ANY_KEY")

        assert list(dev_sandbox.list_env_vars()) == []

    def test_upsert_env_vars_multiple(self, dev_sandbox):
        """测试多次更新环境变量"""
        # 初始环境变量为空
        assert list(dev_sandbox.list_env_vars()) == []

        # 多次更新环境变量
        dev_sandbox.upsert_env_var(key="VAR1", value="value1")
        dev_sandbox.upsert_env_var(key="VAR2", value="value2")
        dev_sandbox.upsert_env_var(key="VAR1", value="updated_value")

        result = dev_sandbox.list_env_vars()
        assert len(result) == 2
        assert result.map["VAR1"].value == "updated_value"
        assert result.map["VAR1"].source == "custom"
        assert result.map["VAR2"].value == "value2"
        assert result.map["VAR2"].source == "custom"
