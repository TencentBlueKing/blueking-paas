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
from django_dynamic_fixture import G

from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "environment_name",
    [ConfigVarEnvName.GLOBAL.value, ConfigVarEnvName.STAG.value, ConfigVarEnvName.PROD.value],
)
def test_get_preset_config_var(api_client, bk_module, environment_name):
    G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.GLOBAL, key="GLOBAL", value="1")
    G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.STAG, key="STAG", value="1")
    G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.PROD, key="PROD", value="1")

    params = {"environment_name": environment_name}
    # url 定义的时候使用了 make_app_pattern，使用 reverse("api.preset_config_vars") 来获取请求路径会导致缺省 module 模块相关的路径
    path = f"/api/bkapps/applications/{bk_module.application.code}/modules/{bk_module.name}/config_vars/preset/"
    response = api_client.get(path, params)
    assert response.data[0]["environment_name"] == environment_name
