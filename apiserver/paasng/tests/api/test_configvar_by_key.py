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

from paasng.platform.applications.models import ApplicationEnvironment
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models import ConfigVar

pytestmark = pytest.mark.django_db

global_env = ConfigVarEnvName.GLOBAL.value
stag_env = ConfigVarEnvName.STAG.value
prod_env = ConfigVarEnvName.PROD.value


@pytest.mark.parametrize(
    ("init_env", "init_value", "update_env", "update_value", "expected_envs", "expected_values"),
    [
        # 1. key 不存在，设置 stag
        (None, None, stag_env, "v1", [stag_env], ["v1"]),
        # 2. key 已存在（stag），更新 prod，查到2个
        (stag_env, "stag_v", prod_env, "prod_v", [stag_env, prod_env], ["stag_v", "prod_v"]),
        # 3. key 已存在（prod），更新 prod
        (prod_env, "old_prod", prod_env, "new_prod", [prod_env], ["new_prod"]),
        # 4. key 已存在（GLOBAL），更新 prod，查到2个
        (global_env, "global_v", prod_env, "prod_v", [global_env, prod_env], ["global_v", "prod_v"]),
    ],
)
def test_configvar_by_key(
    api_client, bk_module, init_env, init_value, update_env, update_value, expected_envs, expected_values
):
    module = bk_module
    env_key = "FOO"
    # 环境准备
    if init_env:
        if init_env == global_env:
            # global 环境的值是 -1
            env_obj = -1
            ConfigVar.objects.create(
                module=module,
                key=env_key,
                environment_id=env_obj,
                value=init_value,
                description="desc",
                is_global=True,
            )
        else:
            env_obj = ApplicationEnvironment.objects.get(module=module, environment=init_env)
            ConfigVar.objects.create(
                module=module, key=env_key, environment=env_obj, value=init_value, description="desc"
            )

    path = f"/api/bkapps/applications/{bk_module.application.code}/modules/{bk_module.name}/config_vars/{env_key}/"
    # 执行 upsert
    resp = api_client.post(
        path,
        data={"environment_name": update_env, "value": update_value, "description": "desc2"},
        format="json",
    )
    assert resp.status_code == 201

    # 查询
    resp = api_client.get(path)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == len(expected_envs)
    env_map = {d["environment_name"]: d["value"] for d in data}
    for env, val in zip(expected_envs, expected_values):
        assert env_map[env] == val

    # 添加对 is_global 的测试
    for item in data:
        if item["environment_name"] == global_env:
            assert item["is_global"] is True
        else:
            assert item["is_global"] is False
