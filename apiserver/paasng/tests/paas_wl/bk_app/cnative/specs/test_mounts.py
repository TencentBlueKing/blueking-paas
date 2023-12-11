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
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource as ConfigMapSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.bk_app.cnative.specs.models import ConfigMapSource, Mount
from paas_wl.infras.resources.base.kres import KNamespace
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.workloads.configuration.configmap.kres_entities import configmap_kmodel

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture(autouse=True)
def _create_mounts(bk_module):
    Mount.objects.create(
        module_id=bk_module.id,
        environment_name=MountEnvName.STAG,
        mount_path="/etc/conf",
        name="nginx",
        source_type=VolumeSourceType.ConfigMap,
        source_config=VolumeSource(configMap=ConfigMapSourceSpec(name="nginx-configmap")),
    )
    Mount.objects.create(
        module_id=bk_module.id,
        environment_name=MountEnvName.GLOBAL.value,
        mount_path="/etc/redis",
        name="redis",
        source_type=VolumeSourceType.ConfigMap,
        source_config=VolumeSource(configMap=ConfigMapSourceSpec(name="redis-configmap")),
    )
    Mount.objects.create(
        module_id=bk_module.id,
        environment_name=MountEnvName.PROD.value,
        mount_path="/etc/redis",
        name="redis",
        source_type=VolumeSourceType.ConfigMap,
        source_config=VolumeSource(configMap=ConfigMapSourceSpec(name="redis-configmap")),
    )


class TestVolumeSourceManager:
    @pytest.fixture(autouse=True)
    def _create_configmap_resource(self, bk_module):
        ConfigMapSource.objects.create(
            application_id=bk_module.application_id,
            name="nginx-configmap",
            module_id=bk_module.id,
            environment_name=MountEnvName.STAG,
            data={"nginx.conf": "location / { }"},
        )
        ConfigMapSource.objects.create(
            application_id=bk_module.application_id,
            name="redis-configmap",
            module_id=bk_module.id,
            environment_name=MountEnvName.GLOBAL,
            data={"redis.conf": "port 6379"},
        )

    @pytest.fixture()
    def _create_namespace(self, bk_stag_env, _with_wl_apps):
        wl_app = bk_stag_env.wl_app
        with get_client_by_app(wl_app) as client:
            body = {
                "metadata": {"name": wl_app.namespace},
            }
            KNamespace(client).create_or_update(
                bk_stag_env.wl_app.namespace,
                body=body,
                update_method="patch",
            )
            yield
            KNamespace(client).delete(bk_stag_env.wl_app.namespace)

    @pytest.fixture()
    def mount(self, bk_app, bk_module):
        mount = Mount.objects.new(
            app_code=bk_app.code,
            module_id=bk_module.id,
            mount_path="/path/",
            environment_name=MountEnvName.GLOBAL,
            name="mount-configmap",
            source_type=VolumeSourceType.ConfigMap.value,
            region=bk_app.region,
        )
        source_data = {"configmap_x": "configmap_x_data", "configmap_y": "configmap_y_data"}
        Mount.objects.upsert_source(mount, source_data)
        return mount

    @pytest.mark.usefixtures("_create_namespace")
    def test_deploy(self, bk_stag_env):
        mounts.VolumeSourceManager(bk_stag_env).deploy()

    @pytest.mark.usefixtures("_create_namespace")
    def test_delete(self, bk_stag_env, mount):
        mounts.VolumeSourceManager(bk_stag_env).deploy()
        assert configmap_kmodel.get(app=bk_stag_env.wl_app, name=mount.source.name)
        mounts.VolumeSourceManager(bk_stag_env).delete_source_config(mount)
        with pytest.raises(AppEntityNotFound):
            configmap_kmodel.get(app=bk_stag_env.wl_app, name=mount.source.name)
