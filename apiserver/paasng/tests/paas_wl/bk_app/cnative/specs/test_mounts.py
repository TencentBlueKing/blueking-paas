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

from paas_wl.bk_app.cnative.specs import mounts
from paas_wl.bk_app.cnative.specs.constants import MountEnvName, VolumeSourceType
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource as ConfigMapSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import PersistentStorage as PersistentStorageSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.bk_app.cnative.specs.models import ConfigMapSource, Mount, PersistentStorageSource
from paas_wl.bk_app.cnative.specs.mounts import MountManager, init_volume_source_controller
from paas_wl.infras.resources.base.kres import KNamespace
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.workloads.configuration.configmap.kres_entities import configmap_kmodel
from paas_wl.workloads.volume.persistent_volume_claim.kres_entities import pvc_kmodel

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
    Mount.objects.create(
        module_id=bk_module.id,
        environment_name=MountEnvName.STAG.name,
        mount_path="/etc/etcd",
        name="etcd",
        source_type=VolumeSourceType.PersistentStorage,
        source_config=VolumeSource(persistentStorage=PersistentStorageSpec(name="etcd-pvc")),
    )


class TestVolumeSourceController:
    @pytest.fixture(autouse=True)
    def _create_configmap_resource(self, bk_module):
        ConfigMapSource.objects.create(
            application_id=bk_module.application_id,
            module_id=bk_module.id,
            name="nginx-configmap",
            environment_name=MountEnvName.STAG,
            data={"nginx.conf": "location / { }"},
        )
        ConfigMapSource.objects.create(
            application_id=bk_module.application_id,
            module_id=bk_module.id,
            name="redis-configmap",
            environment_name=MountEnvName.GLOBAL,
            data={"redis.conf": "port 6379"},
        )
        PersistentStorageSource.objects.create(
            application_id=bk_module.application_id,
            module_id=bk_module.id,
            name="etcd-pvc",
            environment_name=MountEnvName.STAG,
            storage_size="1Gi",
            storage_class_name="cfs",
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

    @pytest.mark.usefixtures("_create_namespace")
    def test_deploy(self, bk_stag_env):
        mounts.deploy_volume_source(bk_stag_env)

    @pytest.fixture()
    def mount_configmap(self, bk_app, bk_module):
        mount = MountManager.new(
            app_code=bk_app.code,
            module_id=bk_module.id,
            mount_path="/path/",
            environment_name=MountEnvName.GLOBAL,
            name="mount-configmap",
            source_type=VolumeSourceType.ConfigMap.value,
        )
        source_data = {"configmap_x": "configmap_x_data", "configmap_y": "configmap_y_data"}
        controller = init_volume_source_controller(mount.source_type)
        controller.create_by_env(
            app_id=mount.module.application.id,
            module_id=mount.module.id,
            env_name=mount.environment_name,
            source_name=mount.get_source_name,
            data=source_data,
        )
        return mount

    @pytest.mark.usefixtures("_create_namespace")
    def test_delete_configmap(self, bk_stag_env, mount_configmap):
        mounts.deploy_volume_source(bk_stag_env)
        controller = init_volume_source_controller(mount_configmap.source_type)
        source = controller.get_by_env(
            app_id=mount_configmap.module.application.id,
            env_name=mount_configmap.environment_name,
            source_name=mount_configmap.get_source_name,
        )
        assert configmap_kmodel.get(app=bk_stag_env.wl_app, name=source.name)
        controller.delete_k8s_resource(source, bk_stag_env.wl_app)
        with pytest.raises(AppEntityNotFound):
            configmap_kmodel.get(app=bk_stag_env.wl_app, name=source.name)

    @pytest.fixture()
    def mount_pvc(self, bk_app, bk_module):
        mount = MountManager.new(
            app_code=bk_app.code,
            module_id=bk_module.id,
            mount_path="/path/",
            environment_name=MountEnvName.STAG,
            name="mount-pvc",
            source_type=VolumeSourceType.PersistentStorage.value,
            source_name="etcd-pvc",
        )
        return mount

    @pytest.mark.usefixtures("_create_namespace")
    def test_delete_pvc(self, bk_stag_env, mount_pvc):
        mounts.deploy_volume_source(bk_stag_env)
        controller = init_volume_source_controller(mount_pvc.source_type)
        source = controller.get_by_env(
            app_id=mount_pvc.module.application.id,
            env_name=mount_pvc.environment_name,
            source_name=mount_pvc.get_source_name,
        )
        assert pvc_kmodel.get(app=bk_stag_env.wl_app, name=source.name)
        controller.delete_k8s_resource(source, bk_stag_env.wl_app)
        with pytest.raises(AppEntityNotFound):
            pvc_kmodel.get(app=bk_stag_env.wl_app, name=source.name)
