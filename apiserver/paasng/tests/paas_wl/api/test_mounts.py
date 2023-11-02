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
from unittest.mock import patch

import pytest

from paas_wl.bk_app.cnative.specs.constants import MountEnvName, VolumeSourceType
from paas_wl.bk_app.cnative.specs.models import Mount
from paas_wl.bk_app.cnative.specs.serializers import MountSLZ

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


@pytest.fixture
def mount(bk_app, bk_module):
    """创建一个 mount 对象"""
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


@pytest.fixture
def mounts(bk_app, bk_module):
    """创建一个包含 15 个 mount 对象的集合"""
    mount_list = []

    for i in range(15):
        mount = Mount.objects.new(
            app_code=bk_app.code,
            module_id=bk_module.id,
            mount_path=f"/{i}",
            environment_name=MountEnvName.GLOBAL,
            name=f"mount-configmap-{i}",
            source_type=VolumeSourceType.ConfigMap.value,
            region=bk_app.region,
        )
        source_data = {"configmap_x": f"configmap_x_data_{i}", "configmap_y": f"configmap_y_data_{i}"}
        Mount.objects.upsert_source(mount, source_data)
        mount_list.append(mount)
    return mount_list


@pytest.fixture(autouse=True, scope="class")
def mock_volume_source_manager():
    with patch(
        "paas_wl.bk_app.cnative.specs.mounts.VolumeSourceManager.delete_source_config", return_value=None
    ), patch("paas_wl.bk_app.cnative.specs.mounts.VolumeSourceManager.__init__", return_value=None):
        yield


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

    def test_create(self, api_client, bk_app, bk_module):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/"
        request_body = {
            "environment_name": "_global_",
            "source_config_data": {"configmap_z": "configmap_z_data"},
            "mount_path": "/path/",
            "name": "mount-configmap-test",
            "source_type": "ConfigMap",
        }
        response = api_client.post(url, request_body)
        mount = Mount.objects.filter(module_id=bk_module.id, mount_path="/path/", name="mount-configmap-test").first()
        assert response.status_code == 201
        assert mount
        assert mount.source.data == {"configmap_z": "configmap_z_data"}

    @pytest.mark.parametrize(
        "request_body_error",
        [
            {
                # 创建相同 unique_together = ('module_id', 'mount_path', 'environment_name') 的 Mount
                "environment_name": "_global_",
                "source_config_data": {"configmap_z": "configmap_z_data"},
                "mount_path": "/path/",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建错误挂载路径的 Mount
                "environment_name": "_global_",
                "source_config_data": {"configmap_z": "configmap_z_data"},
                "mount_path": "path/",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建空挂载内容的 Mount
                "environment_name": "_global_",
                "source_config_data": {},
                "mount_path": "/path",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建挂载内容为数组的 Mount
                "environment_name": "_global_",
                "source_config_data": ["configmap_x", "configmap_y"],
                "mount_path": "/path",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建挂载内容 key 为空的 Mount
                "environment_name": "_global_",
                "source_config_data": {"": "configmap_z_data", "configmap_z": "configmap_z_data"},
                "mount_path": "/path",
                "name": "mount-configmap-test",
                "source_type": "ConfigMap",
            },
            {
                # 创建相同环境下重名的 Mount
                "environment_name": "stag",
                "source_config_data": {"configmap_x": "configmap_z_data", "configmap_z": "configmap_z_data"},
                "mount_path": "/path",
                "name": "mount-configmap",
                "source_type": "ConfigMap",
            },
        ],
    )
    def test_create_error(self, api_client, bk_app, bk_module, mount, request_body_error):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/"
        response = api_client.post(url, request_body_error)
        assert response.status_code == 400

    def test_updata(self, api_client, bk_app, bk_module, mount):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/{mount.id}/"
        body = MountSLZ(mount).data
        body["source_config_data"] = {"configmap_z": "configmap_z_data_updated"}
        body["environment_name"] = "stag"

        response = api_client.put(url, body)
        mount_updated = Mount.objects.get(pk=mount.pk)

        assert response.status_code == 200
        assert mount_updated.name == mount.name
        assert mount_updated.source.data == {"configmap_z": "configmap_z_data_updated"}
        assert mount_updated.source.environment_name == "stag"

        body["name"] = "mount-configmap-test"
        response = api_client.put(url, body)
        mount_updated = Mount.objects.get(pk=mount.pk)

        assert response.status_code == 200
        assert mount_updated.name == "mount-configmap-test"

    def test_destroy(self, api_client, bk_app, bk_module, mount):
        url = "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/{mount.id}/"
        response = api_client.delete(url)
        mount_query = Mount.objects.filter(id=mount.id)
        assert response.status_code == 204
        assert not mount_query.exists()

    def test_destroy_error(self, api_client, bk_app, bk_module, mount):
        # 删除不存在的 mount
        non_existent_id = 999999999
        url = (
            "/api/bkapps/applications/" f"{bk_app.code}/modules/{bk_module.name}/mres/volume_mounts/{non_existent_id}/"
        )
        response = api_client.delete(url)
        mount_query = Mount.objects.filter(id=mount.id)
        assert response.status_code == 404
        assert mount_query.exists()
