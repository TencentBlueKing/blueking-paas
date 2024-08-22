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
from typing import Dict

import pytest
from django_dynamic_fixture import G

from paasng.platform.bkapp_model.entities import EnvVar, EnvVarOverlay
from paasng.platform.engine.configurations import preset_envvars
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.preset_envvars import PresetEnvVariable

pytestmark = pytest.mark.django_db


class Test__batch_save:
    def test_integrated(self, bk_module):
        G(PresetEnvVariable, module=bk_module, environment_name=ConfigVarEnvName.GLOBAL, key="KEY_LEGACY")
        preset_envvars.batch_save(
            bk_module,
            env_vars=[EnvVar(name="KEY1", value="val1"), EnvVar(name="KEY2", value="val2")],
            overlay_env_vars=[EnvVarOverlay(env_name="stag", name="KEY3", value="val3")],
        )

        assert self.to_dict(PresetEnvVariable.objects.filter(module=bk_module)) == {
            (ConfigVarEnvName.GLOBAL, "KEY1"): "val1",
            (ConfigVarEnvName.GLOBAL, "KEY2"): "val2",
            (ConfigVarEnvName.STAG, "KEY3"): "val3",
        }, "The legacy global key should be removed."

        # Save again, this time only provide an item of prod environment
        preset_envvars.batch_save(
            bk_module,
            env_vars=[],
            overlay_env_vars=[EnvVarOverlay(env_name="prod", name="KEY4", value="val4")],
        )
        assert self.to_dict(PresetEnvVariable.objects.filter(module=bk_module)) == {
            (ConfigVarEnvName.PROD, "KEY4"): "val4",
        }, "All existent keys should be removed."

        # Save with empty input should remove all data
        preset_envvars.batch_save(bk_module, [], [])
        assert not PresetEnvVariable.objects.filter(module=bk_module).exists()

    @staticmethod
    def to_dict(qs) -> Dict:
        """Turn PresetEnvVariable queryset to dict for easy comparison."""
        return {(ConfigVarEnvName(var.environment_name), var.key): var.value for var in qs}
