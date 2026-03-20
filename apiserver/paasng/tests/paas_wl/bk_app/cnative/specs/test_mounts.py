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

from unittest.mock import patch

import pytest

from paas_wl.bk_app.cnative.specs import mounts
from paas_wl.bk_app.cnative.specs.constants import MountEnvName, VolumeSourceType
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource as ConfigMapSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import PersistentStorage as PersistentStorageSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.bk_app.cnative.specs.models import (
    ConfigMapSource,
    Mount,
    MountDeploymentSnapshot,
    PersistentStorageSource,
)
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
            tenant_id=bk_app.tenant_id,
        )
        source_data = {"configmap_x": "configmap_x_data", "configmap_y": "configmap_y_data"}
        controller = init_volume_source_controller(mount.source_type)
        controller.create_by_env(
            app_id=mount.module.application.id,
            module_id=mount.module.id,
            env_name=mount.environment_name,
            source_name=mount.source_name,
            tenant_id=bk_app.tenant_id,
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
            source_name=mount_configmap.source_name,
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
            tenant_id=bk_app.tenant_id,
        )
        return mount

    @pytest.mark.usefixtures("_create_namespace")
    def test_delete_pvc(self, bk_stag_env, mount_pvc):
        mounts.deploy_volume_source(bk_stag_env)
        controller = init_volume_source_controller(mount_pvc.source_type)
        source = controller.get_by_env(
            app_id=mount_pvc.module.application.id,
            env_name=mount_pvc.environment_name,
            source_name=mount_pvc.source_name,
        )
        assert pvc_kmodel.get(app=bk_stag_env.wl_app, name=source.name)
        controller.delete_k8s_resource(source, bk_stag_env.wl_app)
        with pytest.raises(AppEntityNotFound):
            pvc_kmodel.get(app=bk_stag_env.wl_app, name=source.name)


class TestBuildDesiredSnapshot:
    """Test build_desired_snapshot pure data function."""

    def test_stag_env_includes_global(self, bk_module):
        """stag 环境应包含 stag + _global_ 的 mount"""
        result = mounts.build_desired_snapshot(bk_module.id, "stag")
        source_names = {item["source_name"] for item in result}
        assert source_names == {"nginx-configmap", "redis-configmap", "etcd-pvc"}

    def test_prod_env_includes_global(self, bk_module):
        """prod 环境应包含 prod + _global_ 的 mount, 不包含 stag 专属"""
        result = mounts.build_desired_snapshot(bk_module.id, "prod")
        source_names = {item["source_name"] for item in result}
        assert source_names == {"redis-configmap"}

    def test_empty_when_no_mounts(self, bk_module):
        """没有 mount 时返回空列表"""
        Mount.objects.filter(module_id=bk_module.id).delete()
        assert mounts.build_desired_snapshot(bk_module.id, "stag") == []


class TestMountDeploymentSnapshotDiff:
    """Test MountDeploymentSnapshot.diff — pure in-memory logic, no DB needed."""

    def test_returns_items_not_in_desired(self):
        """old 中有但 desired 中没有的应被返回"""
        snapshot = MountDeploymentSnapshot(
            [
                {"source_type": "ConfigMap", "source_name": "cm-old"},
                {"source_type": "ConfigMap", "source_name": "cm-keep"},
            ]
        )
        desired = [{"source_type": "ConfigMap", "source_name": "cm-keep"}]
        assert snapshot.diff(desired) == [{"source_type": "ConfigMap", "source_name": "cm-old"}]

    def test_returns_empty_when_no_diff(self):
        """old 和 desired 完全一致时返回空列表"""
        data = [{"source_type": "ConfigMap", "source_name": "cm-a"}]
        assert MountDeploymentSnapshot(snapshot_data=data).diff(data) == []

    def test_diff_considers_both_type_and_name(self):
        """source_type 不同但 source_name 相同时应视为不同资源"""
        snapshot = MountDeploymentSnapshot(snapshot_data=[{"source_type": "ConfigMap", "source_name": "foo"}])
        desired = [{"source_type": "PersistentStorage", "source_name": "foo"}]
        to_delete = snapshot.diff(desired)
        assert to_delete == [{"source_type": "ConfigMap", "source_name": "foo"}]


class TestCleanupVolumeSourceBySnapshot:
    """Test cleanup_volume_source_by_snapshot flow control."""

    def test_first_deploy_skips_delete_and_writes_snapshot(self, bk_stag_env, bk_module):
        """首次部署 (无 snapshot) 应跳过 delete, 直接写入 snapshot"""

        assert not MountDeploymentSnapshot.objects.filter(module_id=bk_module.id, environment_name="stag").exists()

        with patch.object(mounts.ConfigMapSourceController, "delete_k8s_resource_by_name") as mock_delete:
            mounts.cleanup_volume_source_by_snapshot(bk_stag_env)
            mock_delete.assert_not_called()

        snapshot = MountDeploymentSnapshot.objects.get(module_id=bk_module.id, environment_name="stag")
        assert len(snapshot.snapshot_data) > 0

    def test_second_deploy_deletes_removed_sources(self, bk_stag_env, bk_module):
        """第二次部署时, snapshot 中有但 desired 中没有的 ConfigMap 应被删除"""

        # 预置一个包含 stale configmap 的 snapshot
        MountDeploymentSnapshot.objects.create(
            module_id=bk_module.id,
            environment_name="stag",
            snapshot_data=[
                {"source_type": "ConfigMap", "source_name": "stale-configmap"},
                {"source_type": "ConfigMap", "source_name": "nginx-configmap"},
            ],
        )

        with patch.object(mounts.ConfigMapSourceController, "delete_k8s_resource_by_name") as mock_delete:
            mounts.cleanup_volume_source_by_snapshot(bk_stag_env)
            # stale-configmap 不在 desired 中, 应被删除
            deleted_names = {call.args[0] for call in mock_delete.call_args_list}
            assert "stale-configmap" in deleted_names
            # nginx-configmap 仍在 desired 中, 不应被删除
            assert "nginx-configmap" not in deleted_names

    def test_persistent_storage_is_not_deleted(self, bk_stag_env, bk_module):
        """PersistentStorage 类型的资源不应被 cleanup 删除"""

        MountDeploymentSnapshot.objects.create(
            module_id=bk_module.id,
            environment_name="stag",
            snapshot_data=[
                {"source_type": "PersistentStorage", "source_name": "stale-pvc"},
            ],
        )

        with patch.object(mounts.PersistentStorageSourceController, "delete_k8s_resource_by_name") as mock_delete:
            mounts.cleanup_volume_source_by_snapshot(bk_stag_env)
            mock_delete.assert_not_called()
