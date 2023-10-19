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

from paasng.platform.bkapp_model.importer.exceptions import ManifestImportError
from paasng.platform.bkapp_model.importer.importer import import_manifest
from paasng.platform.engine.models.config_var import ConfigVar

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_manifest(bk_app):
    """A very basic manifest that can pass the validation."""
    return {
        'kind': 'BkApp',
        'apiVersion': 'paas.bk.tencent.com/v1alpha2',
        'metadata': {'name': bk_app.code},
        'spec': {
            'build': {'image': 'nginx:latest'},
            'processes': [{'name': 'web'}],
        },
    }


class TestEnvVars:
    def test_invalid_name_input(self, bk_module, base_manifest):
        # Names in lower case are forbidden.
        base_manifest['spec']['configuration'] = {'env': [{'name': 'foo', 'value': 'foo'}]}
        with pytest.raises(ManifestImportError) as e:
            import_manifest(bk_module, base_manifest)

        assert 'configuration.env.0.name' in str(e)

    def test_normal(self, bk_module, base_manifest):
        base_manifest['spec']['configuration'] = {'env': [{'name': 'KEY1', 'value': 'foo'}]}
        base_manifest['spec']['envOverlay'] = {'envVariables': [{'envName': 'stag', 'name': 'KEY2', 'value': 'foo'}]}

        import_manifest(bk_module, base_manifest)
        assert ConfigVar.objects.count() == 2
