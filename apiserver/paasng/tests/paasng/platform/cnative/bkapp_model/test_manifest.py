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
from django_dynamic_fixture import G

from paas_wl.bk_app.cnative.specs.constants import ApiVersion
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource, BkAppSpec, EnvVar, EnvVarOverlay, ObjectMetadata
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.services.models import Plan, Service, ServiceCategory
from paasng.platform.cnative.bkapp_model.manifest import (
    AddonsManifestConstructor,
    EnvVarsManifestConstructor,
    get_manifest,
)
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ConfigVar
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.fixture
def blank_resource() -> BkAppResource:
    """A blank resource object."""
    return BkAppResource(
        apiVersion=ApiVersion.V1ALPHA2, metadata=ObjectMetadata(name='a-blank-resource'), spec=BkAppSpec()
    )


@pytest.fixture
def local_service(bk_app):
    """A local service object."""
    service = G(Service, name='mysql', category=G(ServiceCategory), region=bk_app.region, logo_b64="dummy")
    _ = G(Plan, name=generate_random_string(), service=service)
    return mixed_service_mgr.get(service.uuid, region=bk_app.region)


def test_AddonsManifestConstructor_empty(bk_module, blank_resource):
    AddonsManifestConstructor().apply_to(blank_resource, bk_module)

    annots = blank_resource.metadata.annotations
    assert annots['bkapp.paas.bk.tencent.com/addons'] == '[]'
    assert len(blank_resource.spec.addons) == 0


def test_AddonsManifestConstructor_with_addons(bk_module, blank_resource, local_service):
    mixed_service_mgr.bind_service(local_service, bk_module)
    AddonsManifestConstructor().apply_to(blank_resource, bk_module)

    annots = blank_resource.metadata.annotations
    assert annots['bkapp.paas.bk.tencent.com/addons'] == '["mysql"]'
    assert len(blank_resource.spec.addons) == 1


def test_EnvVarsManifestConstructor_integrated(bk_module, bk_stag_env, blank_resource):
    ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key='FOO_STAG', value='1')
    ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key='BAR', value='1')
    ConfigVar.objects.create(
        module=bk_module,
        environment_id=ENVIRONMENT_ID_FOR_GLOBAL,
        key='BAR',
        value='2',
        is_global=True,
    )

    EnvVarsManifestConstructor().apply_to(blank_resource, bk_module)
    assert blank_resource.spec.configuration.env == [EnvVar(name='BAR', value='2')]
    assert blank_resource.spec.envOverlay.envVariables == [
        EnvVarOverlay(envName='stag', name='BAR', value='1'),
        EnvVarOverlay(envName='stag', name='FOO_STAG', value='1'),
    ]


def test_get_manifest(bk_module):
    manifest = get_manifest(bk_module)
    assert len(manifest) > 0
    assert manifest[0]['kind'] == 'BkApp'
