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

from paas_wl.bk_app.cnative.specs.constants import MountEnvName, VolumeSourceType
from paas_wl.bk_app.cnative.specs.models import ConfigMapSource, Mount, PersistentStorageSource
from paas_wl.bk_app.cnative.specs.mounts import MountManager, init_source_controller
from paas_wl.bk_app.cnative.specs.serializers import MountSLZ

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def mount_configmap(bk_app, bk_module, bk_stag_env, bk_stag_wl_app):
    """创建一个 configmap mount 对象"""
    mount = MountManager.new(
        app_code=bk_app.code,
        module_id=bk_module.id,
        mount_path="/path/",
        environment_name=MountEnvName.STAG,
        name="mount-configmap",
        source_type=VolumeSourceType.ConfigMap.value,
        region=bk_app.region,
    )
    source_data = {"configmap_x": "configmap_x_data", "configmap_y": "configmap_y_data"}
    controller = init_source_controller(mount.source_type)
    controller.create_by_mount(mount, data=source_data)
    return mount


@pytest.fixture()
def pvc_source(bk_app, bk_module):
    pvc = PersistentStorageSource.objects.create(
        application_id=bk_app.id,
        module_id=bk_module.id,
        environment_name=MountEnvName.STAG,
        name="pvc-source-test",
        storage="1Gi",
        storage_class_name="storage-class-test",
    )
    return pvc


@pytest.fixture()
def pvc_source_update(bk_app, bk_module):
    pvc = PersistentStorageSource.objects.create(
        application_id=bk_app.id,
        module_id=bk_module.id,
        environment_name=MountEnvName.STAG,
        name="pvc-source-test-update",
        storage="1Gi",
        storage_class_name="storage-class-test",
    )
    return pvc


@pytest.fixture()
def mount_pvc(bk_app, bk_module, pvc_source):
    """创建一个 pvc mount 对象"""
    mount = MountManager.new(
        app_code=bk_app.code,
        module_id=bk_module.id,
        mount_path="/path/",
        environment_name=MountEnvName.STAG,
        name="mount-pvc",
        source_type=VolumeSourceType.PersistentStorage.value,
        region=bk_app.region,
        source_name=pvc_source.name,
    )
    return mount


@pytest.fixture()
def mounts(bk_app, bk_module):
    """创建一个包含 15 个 mount 对象的集合"""
    mount_list = []

    for i in range(15):
        mount = MountManager.new(
            app_code=bk_app.code,
            module_id=bk_module.id,
            mount_path=f"/{i}",
            environment_name=MountEnvName.GLOBAL,
            name=f"mount-configmap-{i}",
            source_type=VolumeSourceType.ConfigMap.value,
            region=bk_app.region,
        )
        source_data = {"configmap_x": f"configmap_x_data_{i}", "configmap_y": f"configmap_y_data_{i}"}
        controller = init_source_controller(mount.source_type)
        controller.create_by_mount(mount, data=source_data)
        mount_list.append(mount)
    return mount_list


class TestVolumeMountViewSet:
    def test_list(self, api_client, bk_app, bk_module, mounts):
        url = (
            "/api/bkapps/applications/"
            f"{bk_app.code}/modules"
            f"/{bk_module.name}/mres/volume_mounts/?limit=10&offset=0"
        )
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 15
        assert len(response.data["results"]) == 10

        url = (
            "/api/bkapps/applications/"
            f"{bk_app.code}/modules"
            f"/{bk_module.name}/mres/volume_mounts/?limit=10&offset=0&environment_name=stag&source_type=ConfigMap"
        )
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 0
        assert len(response.data["results"]) == 0

    def test_create_configmap(self, api_client, bk_app, bk_module):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/"
        request_body = {
            "environment_name": "_global_",
            "configmap_source": {"source_config_data": {"configmap_z": "configmap_z_data"}},
            "mount_path": "/path/",
            "name": "mount-configmap-test",
            "source_type": "ConfigMap",
        }
        response = api_client.post(url, request_body)
        mount = Mount.objects.filter(module_id=bk_module.id, mount_path="/path/", name="mount-configmap-test").first()
        controller = init_source_controller(mount.source_type)
        source = controller.get_by_mount(mount)
        assert response.status_code == 201
        assert mount
        assert source.data == {"configmap_z": "configmap_z_data"}

    def test_create_pvc(self, api_client, bk_app, bk_module, pvc_source):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/"
        request_body = {
            "environment_name": "stag",
            "mount_path": "/path/",
            "name": "mount-pvc-test",
            "source_type": "PersistentStorage",
            "source_name": pvc_source.name,
        }
        response = api_client.post(url, request_body)
        mount = Mount.objects.filter(module_id=bk_module.id, mount_path="/path/", name="mount-pvc-test").first()
        controller = init_source_controller(mount.source_type)
        source = controller.get_by_mount(mount)
        assert response.status_code == 201
        assert mount
        assert source.storage == pvc_source.storage

    def test_create_with_source_name(self, api_client, bk_app, bk_module, pvc_source):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/"
        request_body = {
            "environment_name": pvc_source.environment_name,
            "mount_path": "/path/",
            "name": "mount-pvc-test",
            "source_type": "PersistentStorage",
            "source_name": pvc_source.name,
        }
        response = api_client.post(url, request_body)
        mount = Mount.objects.filter(module_id=bk_module.id, mount_path="/path/", name="mount-pvc-test").first()
        assert response.status_code == 201
        assert mount.source_config.persistentStorage.name == pvc_source.name

    @pytest.mark.parametrize(
        "request_body_error",
        [
            {
                # 创建相同 unique_together = ('module_id', 'mount_path', 'environment_name') 的 Mount
                "environment_name": "stag",
                "configmap_source": {"source_config_data": {"configmap_z": "configmap_z_data"}},
                "mount_path": "/path/",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建错误挂载路径的 Mount
                "environment_name": "_global_",
                "configmap_source": {"source_config_data": {"configmap_z": "configmap_z_data"}},
                "mount_path": "path/",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建错误挂载路径的 Mount
                "environment_name": "_global_",
                "configmap_source": {"source_config_data": {"configmap_z": "configmap_z_data"}},
                "mount_path": "/",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建空挂载内容的 Mount
                "environment_name": "_global_",
                "configmap_source": {"source_config_data": {}},
                "mount_path": "/path",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建挂载内容为数组的 Mount
                "environment_name": "_global_",
                "configmap_source": {"source_config_data": ["configmap_x", "configmap_y"]},
                "mount_path": "/path",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建挂载内容 key 为空的 Mount
                "environment_name": "_global_",
                "configmap_source": {
                    "source_config_data": {"": "configmap_z_data", "configmap_z": "configmap_z_data"}
                },
                "mount_path": "/path",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建相同环境下重名的 Mount
                "environment_name": "stag",
                "configmap_source": {
                    "source_config_data": {"configmap_x": "configmap_z_data", "configmap_z": "configmap_z_data"}
                },
                "mount_path": "/path",
                "name": "mount-configmap",
                "source_type": "ConfigMap",
            },
        ],
    )
    def test_create_error(self, api_client, bk_app, bk_module, mount_configmap, request_body_error):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/"
        response = api_client.post(url, request_body_error)
        assert response.status_code == 400

    def test_update_configmap(self, api_client, bk_app, bk_module, mount_configmap):
        url = (
            "/api/bkapps/applications/"
            f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/{mount_configmap.id}/"
        )
        body = MountSLZ(mount_configmap).data
        body["configmap_source"] = {"source_config_data": {"configmap_z": "configmap_z_data_updated"}}
        body["environment_name"] = "stag"

        response = api_client.put(url, body)
        mount_updated = Mount.objects.get(pk=mount_configmap.pk)
        controller = init_source_controller(mount_updated.source_type)
        source = controller.get_by_mount(mount_updated)
        assert response.status_code == 200
        assert mount_updated.name == mount_configmap.name
        assert source.data == {"configmap_z": "configmap_z_data_updated"}
        assert source.environment_name == "stag"

        body["name"] = "mount-configmap-test"
        response = api_client.put(url, body)
        mount_updated = Mount.objects.get(pk=mount_configmap.pk)

        assert response.status_code == 200
        assert mount_updated.name == "mount-configmap-test"

    def test_destroy_configmap(self, api_client, bk_app, bk_module, mount_configmap):
        url = (
            "/api/bkapps/applications/"
            f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/{mount_configmap.id}/"
        )
        response = api_client.delete(url)
        mount_query = Mount.objects.filter(id=mount_configmap.id)
        assert response.status_code == 204
        assert not mount_query.exists()

    def test_update_pvc(self, api_client, bk_app, bk_module, mount_pvc, pvc_source_update):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/{mount_pvc.id}/"
        body = MountSLZ(mount_pvc).data
        body["name"] = "mount-pvc-test"
        body["source_name"] = pvc_source_update.name
        response = api_client.put(url, body)
        mount_updated = Mount.objects.get(pk=mount_pvc.pk)

        assert response.status_code == 200
        assert mount_updated.name == "mount-pvc-test"
        assert mount_updated.source_config.persistentStorage.name == pvc_source_update.name

    def test_destroy_pvc(self, api_client, bk_app, bk_module, mount_pvc):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/{mount_pvc.id}/"
        response = api_client.delete(url)
        mount_query = Mount.objects.filter(id=mount_pvc.id)
        assert response.status_code == 204
        assert not mount_query.exists()

    def test_destroy_error(self, api_client, bk_app, bk_module, mount_configmap):
        # 删除不存在的 mount
        non_existent_id = 999999999
        url = (
            "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/{non_existent_id}/"
        )
        response = api_client.delete(url)
        mount_query = Mount.objects.filter(id=mount_configmap.id)
        assert response.status_code == 404
        assert mount_query.exists()


class TestMountSourceViewSet:
    @pytest.fixture(autouse=True)
    def _mount_sources(self, bk_app, bk_module):
        ConfigMapSource.objects.create(
            application_id=bk_app.id,
            module_id=bk_module.id,
            name="configmap-etcd",
            environment_name=MountEnvName.GLOBAL.value,
            data={"configmap_x": "configmap_x_data", "configmap_y": "configmap_y_data"},
        )
        ConfigMapSource.objects.create(
            application_id=bk_app.id,
            module_id=bk_module.id,
            name="configmap-redis",
            environment_name=MountEnvName.GLOBAL.value,
            data={"configmap_x": "configmap_x_data", "configmap_y": "configmap_y_data"},
        )
        PersistentStorageSource.objects.create(
            application_id=bk_app.id,
            module_id=bk_module.id,
            name="pvc",
            environment_name=MountEnvName.GLOBAL.value,
            storage_class_name="cfs",
            storage="1Gi",
        )

    @pytest.mark.usefixtures("_mount_sources")
    def test_list(self, api_client, bk_app):
        url = "/api/bkapps/applications/" f"{bk_app.code}/mres/mount_sources/?source_type=ConfigMap"
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 2

        url = "/api/bkapps/applications/" f"{bk_app.code}/mres/mount_sources/?source_type=PersistentStorage"
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1

    @pytest.mark.usefixtures("_mount_sources")
    def test_create(self, api_client, bk_app):
        url = "/api/bkapps/applications/" f"{bk_app.code}/mres/mount_sources/"
        request_body = {
            "environment_name": "stag",
            "source_type": "PersistentStorage",
            "persistent_storage_source": {"storage": "2Gi"},
        }
        response = api_client.post(url, request_body)
        assert response.status_code == 201
        assert response.data["environment_name"] == "stag"
        assert response.data["storage"] == "2Gi"

    @pytest.mark.usefixtures("_mount_sources")
    def test_destroy(self, api_client, bk_app):
        url = (
            "/api/bkapps/applications/"
            f"{bk_app.code}/mres/mount_sources/?source_type=PersistentStorage&source_name=pvc"
        )
        response = api_client.delete(url)
        assert response.status_code == 204
