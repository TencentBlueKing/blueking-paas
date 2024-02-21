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
from typing import Dict, Type, Union

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.constants import (
    DEFAULT_STORAGE_CLASS_NAME,
    MountEnvName,
    VolumeSourceType,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource as ConfigMapSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import PersistentVolumeClaimSource as PersistentVolumeClaimSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.bk_app.cnative.specs.models import ConfigMapSource, Mount, PersistentVolumeClaimSource
from paas_wl.workloads.configuration.configmap.kres_entities import ConfigMap, configmap_kmodel
from paas_wl.workloads.volume.persistent_volume_claim.kres_entities import PersistentVolumeClaim, pvc_kmodel
from paasng.platform.applications.models import ModuleEnvironment


class BaseVolumeSourceController:
    _source_types: Dict[VolumeSourceType, Type["BaseVolumeSourceController"]] = {}  # type: ignore
    volume_source_type: VolumeSourceType

    def __init_subclass__(cls, **kwargs):
        # register subclass to stage_types dict
        cls._source_types[cls.volume_source_type] = cls

    @classmethod
    def get_source_class(cls, volume_source_type: Union[str, VolumeSourceType]) -> Type["BaseVolumeSourceController"]:
        return cls._source_types[VolumeSourceType(volume_source_type)]

    def create_volume_source(self, name: str):
        """创建对应 VolumeSource 对象"""
        raise NotImplementedError

    def list_model_by_app(self, application_id: str):
        """通过应用 ID 查看对应 django model 对象列表"""
        raise NotImplementedError

    def get_model_by_mount(self, mount: Mount):
        """通过 Mount 查看对应 django model 对象"""
        raise NotImplementedError

    def upsert_model_by_mount(self, mount: Mount, **kwargs):
        """通过 Mount 创建/更新对应 django model 对象"""
        raise NotImplementedError

    def upsert_k8s_resource(self, mount: Mount, wl_app: WlApp):
        """创建/更新对应 k8s 资源"""
        raise NotImplementedError

    def delete_k8s_resource(self, mount: Mount, wl_app: WlApp):
        """删除对应 k8s 资源"""
        raise NotImplementedError


class ConfigMapSourceController(BaseVolumeSourceController):
    volume_source_type = VolumeSourceType.ConfigMap

    def create_volume_source(self, name: str):
        return VolumeSource(configMap=ConfigMapSourceSpec(name=name))

    def list_model_by_app(self, application_id: str):
        return ConfigMapSource.objects.filter(application_id=application_id)

    def get_model_by_mount(self, mount: Mount):
        return ConfigMapSource.objects.get_by_mount(mount)

    def upsert_model_by_mount(self, mount: Mount, **kwargs):
        data = kwargs.get("data", {})
        if not mount.source_config.configMap:
            raise ValueError(f"Mount {mount.name} is invalid: source_config.configMap is none")

        config_source, _ = ConfigMapSource.objects.update_or_create(
            name=mount.source_config.configMap.name,
            application_id=mount.module.application_id,
            defaults={
                "module_id": mount.module.id,
                "environment_name": mount.environment_name,
                "data": data,
            },
        )
        return config_source

    def upsert_k8s_resource(self, mount: Mount, wl_app: WlApp):
        source = self.get_model_by_mount(mount)
        configmap_kmodel.upsert(ConfigMap(app=wl_app, name=source.name, data=source.data))

    def delete_k8s_resource(self, mount: Mount, wl_app: WlApp):
        # 检查是否存在其他挂载
        if Mount.objects.filter(source_config=mount.source_config).exclude(pk=mount.pk).exists():
            return
        source = self.get_model_by_mount(mount)
        configmap_kmodel.delete(ConfigMap(app=wl_app, name=source.name, data=source.data))


class PVCSourceController(BaseVolumeSourceController):
    volume_source_type = VolumeSourceType.PersistentVolumeClaim

    def create_volume_source(self, name: str):
        return VolumeSource(persistentVolumeClaim=PersistentVolumeClaimSourceSpec(name=name))

    def list_model_by_app(self, application_id: str):
        return PersistentVolumeClaimSource.objects.filter(application_id=application_id)

    def get_model_by_mount(self, mount: Mount):
        return PersistentVolumeClaimSource.objects.get_by_mount(mount)

    def upsert_model_by_mount(self, mount: Mount, **kwargs):
        if not mount.source_config.persistentVolumeClaim:
            raise ValueError(f"Mount {mount.name} is invalid: source_config.persistentVolumeClaim is none")

        defalults = {
            "module_id": mount.module.id,
            "environment_name": mount.environment_name,
            "storage_class_name": DEFAULT_STORAGE_CLASS_NAME,
        }
        if storage := kwargs.get("storage"):
            defalults["storage"] = storage

        pvc_source, _ = PersistentVolumeClaimSource.objects.update_or_create(
            name=mount.source_config.persistentVolumeClaim.name,
            application_id=mount.module.application_id,
            defaults=defalults,
        )
        return pvc_source

    def upsert_k8s_resource(self, mount: Mount, wl_app: WlApp):
        source = self.get_model_by_mount(mount)
        pvc_kmodel.upsert(
            PersistentVolumeClaim(
                app=wl_app,
                name=source.name,
                storage=source.storage,
                storage_class_name=source.storage_class_name,
            )
        )

    def delete_k8s_resource(self, mount: Mount, wl_app: WlApp):
        # 检查是否存在其他挂载
        if Mount.objects.filter(source_config=mount.source_config).exclude(pk=mount.pk).exists():
            return
        source = self.get_model_by_mount(mount)
        pvc_kmodel.delete(
            PersistentVolumeClaim(
                app=wl_app,
                name=source.name,
                storage=source.storage,
                storage_class_name=source.storage_class_name,
            )
        )


def init_source_controller(volume_source_type: str) -> BaseVolumeSourceController:
    return BaseVolumeSourceController.get_source_class(volume_source_type)()


class VolumeSourceManager:
    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.wl_app = env.wl_app

    def deploy(self):
        mount_queryset = Mount.objects.filter(
            module_id=self.env.module.id, environment_name__in=[self.env.environment, MountEnvName.GLOBAL.value]
        )
        for m in mount_queryset:
            self._upsert(m)

    def _upsert(self, mount: Mount):
        controller = init_source_controller(mount.source_type)
        controller.upsert_k8s_resource(mount, self.wl_app)

    def delete_source_config(self, mount: Mount):
        controller = init_source_controller(mount.source_type)
        controller.delete_k8s_resource(mount, self.wl_app)
