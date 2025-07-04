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

from paasng.platform.engine.configurations.env_var.listers import list_vars_user_configured

pytestmark = pytest.mark.django_db


class TestListVarsUserConfigured:
    def test_empty(self, bk_module, bk_prod_env):
        assert list_vars_user_configured(bk_prod_env).kv_map == {}

    def test_normal(self, bk_module, bk_prod_env, config_var_maker):
        config_var_maker(
            environment_name="prod", module=bk_module, key="DJANGO_SETTINGS_MODULE", value="proj.settings"
        )
        config_var_maker(environment_name="_global_", module=bk_module, key="NAME", value="global")
        result = list_vars_user_configured(bk_prod_env).kv_map
        assert result == {"DJANGO_SETTINGS_MODULE": "proj.settings", "NAME": "global"}

    def test_conflicted_name_across_envs(self, bk_module, config_var_maker, bk_stag_env, bk_prod_env):
        config_var_maker(
            environment_name="prod", module=bk_module, key="DJANGO_SETTINGS_MODULE", value="proj.settings"
        )
        config_var_maker(
            environment_name="_global_", module=bk_module, key="DJANGO_SETTINGS_MODULE", value="global.settings"
        )

        result = list_vars_user_configured(bk_prod_env).kv_map
        assert result == {"DJANGO_SETTINGS_MODULE": "proj.settings"}

        result = list_vars_user_configured(bk_stag_env).kv_map
        assert result == {"DJANGO_SETTINGS_MODULE": "global.settings"}
