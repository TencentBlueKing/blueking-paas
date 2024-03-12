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
import uuid
from typing import Any, Dict, Optional, Type, Union

from django.conf import settings
from django.db.models import QuerySet

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.constants import (
    MountEnvName,
    VolumeSourceType,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource as ConfigMapSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import PersistentStorage as PersistentStorageSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.bk_app.cnative.specs.models import ConfigMapSource, Mount, PersistentStorageSource
from paas_wl.infras.cluster.shim import get_application_cluster
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import KStorageClass
from paas_wl.workloads.configuration.configmap.kres_entities import ConfigMap, configmap_kmodel
from paas_wl.workloads.volume.persistent_volume_claim.kres_entities import PersistentVolumeClaim, pvc_kmodel
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.models import Module


class BaseVolumeSourceController:
    _source_types: Dict[VolumeSourceType, Type["BaseVolumeSourceController"]] = {}  # type: ignore
    volume_source_type: VolumeSourceType
    model_class: Type[Union[ConfigMapSource, PersistentStorageSource]]

    def __init_subclass__(cls, **kwargs):
        # register subclass to stage_types dict
        cls._source_types[cls.volume_source_type] = cls

    @classmethod
    def get_source_class(cls, volume_source_type: Union[str, VolumeSourceType]) -> Type["BaseVolumeSourceController"]:
        return cls._source_types[VolumeSourceType(volume_source_type)]

    def build_volume_source(self, name: str) -> VolumeSource:
        """创建对应 VolumeSource 对象"""
        raise NotImplementedError

    def list_by_app(self, application_id: str) -> Any:
        """通过应用 ID 查看对应 model 对象列表"""
        raise NotImplementedError

    def create_by_app(self, application_id: str, environment_name: str, **kwargs) -> Any:
        """通过应用 ID 创建对应 model 对象"""
        raise NotImplementedError

    def delete_by_app(self, application_id: str, source_name: str) -> None:
        """通过应用 ID 删除对应 model 对象"""
        raise NotImplementedError

    def get_by_env(self, app_id: str, env_name: str, source_name: str) -> Any:
        raise NotImplementedError

    def delete_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str) -> None:
        """通过模块、环境删除对应 model 对象"""
        raise NotImplementedError

    def create_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str, **kwargs) -> Any:
        """通过模块、环境创建/更新对应 model 对象"""
        raise NotImplementedError

    def update_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str, **kwargs) -> Any:
        """通过模块、环境创建/更新对应 model 对象"""
        raise NotImplementedError

    def upsert_k8s_resource(self, source: Union[ConfigMapSource, PersistentStorageSource], wl_app: WlApp) -> None:
        """创建/更新对应 k8s 资源"""
        raise NotImplementedError

    def delete_k8s_resource(self, source: Union[ConfigMapSource, PersistentStorageSource], wl_app: WlApp) -> None:
        """删除对应 k8s 资源"""
        raise NotImplementedError


class ConfigMapSourceController(BaseVolumeSourceController):
    volume_source_type = VolumeSourceType.ConfigMap
    model_class = ConfigMapSource

    def build_volume_source(self, name: str) -> VolumeSource:
        return VolumeSource(configMap=ConfigMapSourceSpec(name=name))

    def list_by_app(self, application_id: str) -> QuerySet[ConfigMapSource]:
        return self.model_class.objects.filter(application_id=application_id)

    def create_by_app(self, application_id: str, environment_name: str, **kwargs) -> None:
        """configmap 类型属于模块级别,暂不支持应用级别单独创建"""
        raise NotImplementedError

    def delete_by_app(self, application_id: str, source_name: str) -> None:
        """configmap 类型属于模块级别,暂不支持应用级别单独删除"""
        raise NotImplementedError

    def get_by_env(self, app_id: str, env_name: str, source_name: str) -> ConfigMapSource:
        return self.model_class.objects.get(
            application_id=app_id,
            environment_name=env_name,
            name=source_name,
        )

    def create_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str, **kwargs) -> ConfigMapSource:
        data = kwargs.get("data", {})

        return self.model_class.objects.create(
            application_id=app_id,
            module_id=module_id,
            environment_name=env_name,
            name=source_name,
            data=data,
        )

    def update_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str, **kwargs) -> ConfigMapSource:
        # 需要删除对应的 k8s volume 资源
        source = self.get_by_env(
            app_id=app_id,
            env_name=env_name,
            source_name=source_name,
        )
        # 删除 mount 对应的 source k8s 资源
        module = Module.objects.get(id=module_id)
        for env in module.get_envs():
            self.delete_k8s_resource(source, env.wl_app)

        # 更新 source 对象
        data = kwargs.get("data", {})
        source.environment_name = env_name
        source.data = data
        source.save(update_fields=["environment_name", "data"])
        return source

    def delete_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str) -> None:
        source = self.get_by_env(
            app_id=app_id,
            env_name=env_name,
            source_name=source_name,
        )

        # 删除 mount 对应的 source k8s 资源
        module = Module.objects.get(id=module_id)
        for env in module.get_envs():
            self.delete_k8s_resource(source, env.wl_app)

        source.delete()

    def upsert_k8s_resource(self, source: ConfigMapSource, wl_app: WlApp) -> None:
        configmap_kmodel.upsert(ConfigMap(app=wl_app, name=source.name, data=source.data))

    def delete_k8s_resource(self, source: ConfigMapSource, wl_app: WlApp) -> None:
        configmap_kmodel.delete(ConfigMap(app=wl_app, name=source.name, data=source.data))


class PersistentStorageSourceController(BaseVolumeSourceController):
    volume_source_type = VolumeSourceType.PersistentStorage
    model_class = PersistentStorageSource

    def build_volume_source(self, name: str) -> VolumeSource:
        return VolumeSource(persistentStorage=PersistentStorageSpec(name=name))

    def list_by_app(self, application_id: str) -> QuerySet[PersistentStorageSource]:
        return self.model_class.objects.filter(application_id=application_id)

    def create_by_app(self, application_id: str, environment_name: str, **kwargs) -> PersistentStorageSource:
        application = Application.objects.get(id=application_id)
        return self.model_class.objects.create(
            application_id=application_id,
            environment_name=environment_name,
            name=generate_source_config_name(app_code=application.code),
            storage_size=kwargs.get("storage_size"),
            storage_class_name=settings.DEFAULT_PERSISTENT_STORAGE_CLASS_NAME,
        )

    def delete_by_app(self, application_id: str, source_name: str) -> None:
        # 删除 k8s 资源
        mounts = Mount.objects.filter(
            source_config=self.build_volume_source(source_name),
        )
        source = self.model_class.objects.get(application_id=application_id, name=source_name)
        for mount in mounts:
            for env in mount.module.get_envs():
                self.delete_k8s_resource(source, env.wl_app)
            mount.delete()

        source.delete()

    def get_by_env(self, app_id: str, env_name: str, source_name: str) -> PersistentStorageSource:
        return self.model_class.objects.get(
            application_id=app_id,
            environment_name=env_name,
            name=source_name,
        )

    def create_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str, **kwargs) -> None:
        """persistent storage 类型属于应用级别,暂不支持模块环境级别创建"""
        return

    def update_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str, **kwargs) -> None:
        """persistent storage 类型属于应用级别,暂不支持模块环境级别更新"""
        return

    def delete_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str) -> None:
        """persistent storage 类型属于应用级别,暂不支持模块环境级别删除"""
        return

    def upsert_k8s_resource(self, source: PersistentStorageSource, wl_app: WlApp) -> None:
        pvc_kmodel.upsert(
            PersistentVolumeClaim(
                app=wl_app,
                name=source.name,
                storage=source.storage_size,
                storage_class_name=source.storage_class_name,
            )
        )

    def delete_k8s_resource(self, source: PersistentStorageSource, wl_app: WlApp) -> None:
        pvc_kmodel.delete(
            PersistentVolumeClaim(
                app=wl_app,
                name=source.name,
                storage=source.storage_size,
                storage_class_name=source.storage_class_name,
            )
        )


def init_volume_source_controller(volume_source_type: str) -> BaseVolumeSourceController:
    return BaseVolumeSourceController.get_source_class(volume_source_type)()


def generate_source_config_name(app_code: str) -> str:
    """Generate name of the Mount source_config"""
    return f"{app_code}-{uuid.uuid4().hex}"


def deploy_volume_source(env: ModuleEnvironment):
    mount_queryset = Mount.objects.filter(
        module_id=env.module.id, environment_name__in=[env.environment, MountEnvName.GLOBAL.value]
    )
    for m in mount_queryset:
        controller = init_volume_source_controller(m.source_type)
        source = controller.get_by_env(
            app_id=m.module.application.id,
            env_name=m.environment_name,
            source_name=m.get_source_name,
        )
        controller.upsert_k8s_resource(source, env.wl_app)


class MountManager:
    @classmethod
    def new(
        cls,
        app_code: str,
        module_id: uuid.UUID,
        name: str,
        environment_name: str,
        mount_path: str,
        source_type: str,
        region: str,
        source_name: Optional[str] = None,
    ) -> Mount:
        source_config_name = source_name or generate_source_config_name(app_code=app_code)
        controller = init_volume_source_controller(source_type)
        source_config = controller.build_volume_source(name=source_config_name)

        return Mount.objects.create(
            module_id=module_id,
            name=name,
            environment_name=environment_name,
            mount_path=mount_path,
            source_type=source_type,
            region=region,
            source_config=source_config,
        )


def check_storage_class_exists(application: Application, storage_class_name: str) -> bool:
    """检查给定的 StorageClass 是否存在于 Kubernetes 集群中。

    :param application: Application object
    :param storage_class_name: 要检查的 StorageClass 的名称。
    :return bool: 如果 StorageClass 存在,返回 True。否则返回 False。
    """
    cluster = get_application_cluster(application)
    with get_client_by_cluster_name(cluster_name=cluster.name) as client:
        storage_class_client = KStorageClass(client)
        try:
            _ = storage_class_client.get(name=storage_class_name)
        except ResourceMissing:
            return False
        else:
            return True
