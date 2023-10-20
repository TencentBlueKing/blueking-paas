"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import pytest

from paas_wl.bk_app.cnative.specs.crd.bk_app import EnvVar, EnvVarOverlay
from paasng.platform.bkapp_model.importer.env_vars import import_env_vars
from paasng.platform.engine.models.config_var import ConfigVar

pytestmark = pytest.mark.django_db


class Test__import_env_vars:
    def test_integrated(self, bk_module):
        ConfigVar.objects.create(module=bk_module, key='KEY_EXISTING')
        env_vars = [EnvVar(name='KEY1', value='foo'), EnvVar(name='KEY2', value='foo')]
        overlay_env_vars = [EnvVarOverlay(envName='stag', name='KEY3', value='foo')]
        ret = import_env_vars(bk_module, env_vars, overlay_env_vars)

        assert ConfigVar.objects.count() == 3
        assert ConfigVar.objects.filter(is_global=True).count() == 2
        assert ret.updated_num == 0
        assert ret.created_num == 3
        assert ret.deleted_num == 1
