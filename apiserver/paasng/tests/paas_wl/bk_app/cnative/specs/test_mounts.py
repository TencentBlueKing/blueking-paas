# -*- coding: utf-8 -*-
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

from paas_wl.bk_app.cnative.specs import mounts
from paas_wl.bk_app.cnative.specs.constants import MountEnvName, VolumeSourceType
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppResource
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource as ConfigMapSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import Mount as MountSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.bk_app.cnative.specs.models import ConfigMapSource, Mount
from paas_wl.infras.resources.base.kres import KNamespace
from paas_wl.infras.resources.utils.basic import get_client_by_app

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(autouse=True)
def create_mounts(bk_module):
    Mount.objects.create(
        module_id=bk_module.id,
        environment_name=MountEnvName.STAG,
        mount_path='/etc/conf',
        name='nginx',
        source_type=VolumeSourceType.ConfigMap,
        source_config=VolumeSource(configMap=ConfigMapSourceSpec(name='nginx-configmap')),
    ),
    Mount.objects.create(
        module_id=bk_module.id,
        environment_name=MountEnvName.GLOBAL.value,
        mount_path='/etc/redis',
        name='redis',
        source_type=VolumeSourceType.ConfigMap,
        source_config=VolumeSource(configMap=ConfigMapSourceSpec(name='redis-configmap')),
    )
    Mount.objects.create(
        module_id=bk_module.id,
        environment_name=MountEnvName.PROD.value,
        mount_path='/etc/redis',
        name='redis',
        source_type=VolumeSourceType.ConfigMap,
        source_config=VolumeSource(configMap=ConfigMapSourceSpec(name='redis-configmap')),
    )


@pytest.fixture
def app_resource(bk_stag_env) -> BkAppResource:
    manifest = {
        'apiVersion': 'paas.bk.tencent.com/v1alpha2',
        'kind': 'BkApp',
        'metadata': {'name': 'bkapp'},
        'spec': {
            'mounts': None,
            'envOverlay': None,
        },
    }
    return BkAppResource(**manifest)


def test_inject_to_app_resource(bk_stag_env, app_resource):
    mounts.inject_to_app_resource(bk_stag_env, app_resource)

    assert len(app_resource.spec.mounts) == 2
    assert app_resource.spec.mounts[0] == MountSpec(
        name='nginx', mountPath='/etc/conf', source=VolumeSource(configMap=ConfigMapSourceSpec(name='nginx-configmap'))
    )
    assert app_resource.spec.mounts[1] == MountSpec(
        name='redis',
        mountPath='/etc/redis',
        source=VolumeSource(configMap=ConfigMapSourceSpec(name='redis-configmap')),
    )


class TestVolumeSourceManager:
    @pytest.fixture(autouse=True)
    def create_configmap_resource(self, bk_module):
        ConfigMapSource.objects.create(
            application_id=bk_module.application_id,
            name='nginx-configmap',
            module_id=bk_module.id,
            environment_name=MountEnvName.STAG,
            data={"nginx.conf": "location / { }"},
        )
        ConfigMapSource.objects.create(
            application_id=bk_module.application_id,
            name='redis-configmap',
            module_id=bk_module.id,
            environment_name=MountEnvName.GLOBAL,
            data={"redis.conf": "port 6379"},
        )

    @pytest.fixture
    def create_namespace(self, bk_stag_env, with_wl_apps):
        wl_app = bk_stag_env.wl_app
        with get_client_by_app(wl_app) as client:
            body = {
                'metadata': {'name': wl_app.namespace},
            }
            KNamespace(client).create_or_update(
                bk_stag_env.wl_app.namespace,
                body=body,
                update_method='patch',
            )
            yield
            KNamespace(client).delete(bk_stag_env.wl_app.namespace)

    def test_deploy(self, create_namespace, bk_stag_env, with_wl_apps):
        mounts.VolumeSourceManager(bk_stag_env).deploy()
