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

from paasng.platform.bkapp_model.entities import EnvVar, EnvVarOverlay
from paasng.platform.bkapp_model.entities_syncer import sync_env_vars
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable
from paasng.utils.structure import NOTSET

pytestmark = pytest.mark.django_db


class Test__sync_env_vars:
    def test_integrated(self, bk_module):
        G(PresetEnvVariable, module=bk_module, key="KEY_EXISTING")
        env_vars = [
            EnvVar(name="KEY1", value="foo", description="desc_1"),
            EnvVar(name="KEY2", value="foo", description="desc_2"),
        ]
        overlay_env_vars = [EnvVarOverlay(env_name="stag", name="KEY3", value="foo", description="desc_3")]
        ret = sync_env_vars(bk_module, env_vars, overlay_env_vars)

        assert PresetEnvVariable.objects.count() == 3
        assert PresetEnvVariable.objects.filter(environment_name=ConfigVarEnvName.GLOBAL.value).count() == 2
        assert ret.updated_num == 0
        assert ret.created_num == 3
        assert ret.deleted_num == 1

        # 测试 description 字段
        expected_variables = [
            {"key": "KEY1", "env_name": ConfigVarEnvName.GLOBAL.value, "description": "desc_1"},
            {"key": "KEY2", "env_name": ConfigVarEnvName.GLOBAL.value, "description": "desc_2"},
            {"key": "KEY3", "env_name": ConfigVarEnvName.STAG.value, "description": "desc_3"},
        ]
        for var in expected_variables:
            assert (
                PresetEnvVariable.objects.get(key=var["key"], environment_name=var["env_name"]).description
                == var["description"]
            )

    def test_notset_remove_all(self, bk_module):
        G(PresetEnvVariable, module=bk_module, key="KEY_EXISTING", environment_name=ConfigVarEnvName.STAG.value)
        sync_env_vars(bk_module, [], NOTSET)

        assert PresetEnvVariable.objects.count() == 0
