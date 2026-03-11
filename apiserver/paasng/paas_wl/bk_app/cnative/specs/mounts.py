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

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import ValidationError

from paas_wl.bk_app.cnative.specs.constants import (
    MountEnvName,
    VolumeSourceType,
)
from paas_wl.bk_app.cnative.specs.crd.bk_app import ConfigMapSource as ConfigMapSourceSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import PersistentStorage as PersistentStorageSpec
from paas_wl.bk_app.cnative.specs.crd.bk_app import VolumeSource
from paas_wl.bk_app.cnative.specs.models import ConfigMapSource, Mount, PersistentStorageSource
from paas_wl.infras.cluster.shim import get_app_prod_env_cluster
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import KStorageClass
from paas_wl.workloads.configuration.configmap.kres_entities import ConfigMap, configmap_kmodel
from paas_wl.workloads.volume.persistent_volume_claim.kres_entities import PersistentVolumeClaim, pvc_kmodel
from paasng.platform.applications.constants import AppFeatureFlag
from paasng.platform.applications.models import Application, ApplicationFeatureFlag, ModuleEnvironment
from paasng.platform.modules.models import Module

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from paas_wl.bk_app.applications.models import WlApp


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

    def create_by_app(self, application_id: str, environment_name: str, tenant_id: str, **kwargs) -> Any:
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

    def create_by_env(
        self, app_id: str, module_id: str, env_name: str, source_name: str, tenant_id: str, **kwargs
    ) -> Any:
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

    def sync_k8s_resource(self, env: ModuleEnvironment, mounts: QuerySet) -> None:
        """同步挂载卷对应的 k8s 资源"""
        raise NotImplementedError


class ConfigMapSourceController(BaseVolumeSourceController):
    volume_source_type = VolumeSourceType.ConfigMap
    model_class = ConfigMapSource

    def build_volume_source(self, name: str) -> VolumeSource:
        return VolumeSource(configMap=ConfigMapSourceSpec(name=name))

    def list_by_app(self, application_id: str) -> QuerySet[ConfigMapSource]:
        return self.model_class.objects.filter(application_id=application_id)

    def create_by_app(self, application_id: str, environment_name: str, tenant_id: str, **kwargs) -> None:
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

    def create_by_env(
        self, app_id: str, module_id: str, env_name: str, source_name: str, tenant_id: str, **kwargs
    ) -> ConfigMapSource:
        data = kwargs.get("data", {})

        return self.model_class.objects.create(
            application_id=app_id,
            module_id=module_id,
            environment_name=env_name,
            name=source_name,
            data=data,
            is_deleted=False,
            tenant_id=tenant_id,
        )

    def update_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str, **kwargs) -> ConfigMapSource:
        # 需要删除对应的 k8s volume 资源
        source = self.model_class.objects.get(
            application_id=app_id,
            name=source_name,
        )
        data = kwargs.get("data", {})

        # 如果环境发生变化, 将旧环境加入 pending_delete_envs 字段
        if source.environment_name != env_name:
            pending = set(source.pending_delete_envs or [])
            # global 环境会部署到所有实际环境，需要把所有实际环境均加入待清理
            if source.environment_name == MountEnvName.GLOBAL:
                module = Module.objects.get(id=module_id)
                for env in module.get_envs():
                    pending.add(env.environment)
            else:
                pending.add(source.environment_name)
            source.pending_delete_envs = list(pending)

        source.environment_name = env_name
        source.data = data
        source.save(update_fields=["environment_name", "data", "pending_delete_envs"])
        return source

    def delete_by_env(self, app_id: str, module_id: str, env_name: str, source_name: str) -> None:
        source = self.get_by_env(
            app_id=app_id,
            env_name=env_name,
            source_name=source_name,
        )

        # 将当前 environment_name 对应的所有实际 k8s 环境加入待清理，下次部署时清理 k8s 资源
        pending = set(source.pending_delete_envs or [])
        if env_name == MountEnvName.GLOBAL:
            module = Module.objects.get(id=module_id)
            for env in module.get_envs():
                pending.add(env.environment)
        else:
            pending.add(env_name)

        source.pending_delete_envs = list(pending)
        source.is_deleted = True
        source.save(update_fields=["pending_delete_envs", "is_deleted"])

    def upsert_k8s_resource(self, source: ConfigMapSource, wl_app: WlApp) -> None:
        configmap_kmodel.upsert(ConfigMap(app=wl_app, name=source.name, data=source.data))

    def delete_k8s_resource(self, source: ConfigMapSource, wl_app: WlApp) -> None:
        configmap_kmodel.delete(ConfigMap(app=wl_app, name=source.name, data=source.data))

    def sync_k8s_resource(self, env: ModuleEnvironment, mounts: QuerySet) -> None:
        # 1. 清理 pending_delete_envs 中包含当前环境的旧 ConfigMap 资源
        # 包含两种情况:
        #   - 修改了 environment_name, 旧环境的 k8s 资源需要删除
        #   - 删除了挂载卷, 旧环境的 k8s 资源需要删除
        pending_sources = self.model_class.objects.filter(
            module_id=env.module.id,
            pending_delete_envs__contains=env.environment,
        )
        for source in pending_sources:
            self.delete_k8s_resource(source, env.wl_app)
            # 从 pending_delete_envs 中移除当前环境
            remaining = [e for e in source.pending_delete_envs if e != env.environment]
            source.pending_delete_envs = remaining
            # 如果是删除挂载卷, 则标记为已删除
            if source.is_deleted and not remaining:
                # 已经被删除, 且所有环境都没清理完, 删除 DB 记录
                source.delete()
            else:
                source.save(update_fields=["pending_delete_envs"])

        # 2. 创建或更新 k8s 资源
        for m in mounts:
            source = self.get_by_env(
                app_id=m.module.application.id,
                env_name=m.environment_name,
                source_name=m.get_source_name,
            )
            self.upsert_k8s_resource(source, env.wl_app)


class PersistentStorageSourceController(BaseVolumeSourceController):
    volume_source_type = VolumeSourceType.PersistentStorage
    model_class = PersistentStorageSource

    def build_volume_source(self, name: str) -> VolumeSource:
        return VolumeSource(persistentStorage=PersistentStorageSpec(name=name))

    def list_by_app(self, application_id: str) -> QuerySet[PersistentStorageSource]:
        return self.model_class.objects.filter(application_id=application_id)

    def create_by_app(
        self, application_id: str, environment_name: str, tenant_id: str, **kwargs
    ) -> PersistentStorageSource:
        application = Application.objects.get(id=application_id)
        params = {
            "application_id": application_id,
            "environment_name": environment_name,
            "name": generate_source_config_name(app_code=application.code),
            "storage_size": kwargs.get("storage_size"),
            "storage_class_name": settings.DEFAULT_PERSISTENT_STORAGE_CLASS_NAME,
            "tenant_id": tenant_id,
        }
        if display_name := kwargs.get("display_name"):
            params["display_name"] = display_name
        return self.model_class.objects.create(**params)

    def delete_by_app(self, application_id: str, source_name: str) -> None:
        # 删除持久存储资源前，需要确保对应挂载卷资源已被删除
        if Mount.objects.filter(source_config=self.build_volume_source(source_name)).exists():
            raise ValidationError(_("删除持久存储资源失败，请先删除相应挂载卷资源"))

        app = Application.objects.get(id=application_id)
        app_envs = app.get_app_envs()
        source = self.model_class.objects.get(application_id=application_id, name=source_name)
        for env in app_envs:
            self.delete_k8s_resource(source, env.wl_app)

        source.delete()

    def get_by_env(self, app_id: str, env_name: str, source_name: str) -> PersistentStorageSource:
        return self.model_class.objects.get(
            application_id=app_id,
            environment_name=env_name,
            name=source_name,
        )

    def create_by_env(
        self, app_id: str, module_id: str, env_name: str, source_name: str, tenant_id: str, **kwargs
    ) -> None:
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

    def sync_k8s_resource(self, env: ModuleEnvironment, mounts: QuerySet) -> None:
        for m in mounts:
            source = self.get_by_env(
                app_id=m.module.application.id,
                env_name=m.environment_name,
                source_name=m.get_source_name,
            )
            self.upsert_k8s_resource(source, env.wl_app)


def init_volume_source_controller(volume_source_type: str) -> BaseVolumeSourceController:
    return BaseVolumeSourceController.get_source_class(volume_source_type)()


def generate_source_config_name(app_code: str) -> str:
    """Generate name of the Mount source_config"""
    return f"{app_code.replace('_', '0us0')}-{uuid.uuid4().hex}"


def sync_volume_source(env: ModuleEnvironment):
    mount_queryset = Mount.objects.filter(
        module_id=env.module.id, environment_name__in=[env.environment, MountEnvName.GLOBAL.value]
    )
    for source_type in VolumeSourceType:
        controller = init_volume_source_controller(source_type)
        controller.sync_k8s_resource(env, mount_queryset.filter(source_type=source_type.value))


class MountManager:
    @classmethod
    def new(
        cls,
        tenant_id: str,
        app_code: str,
        module_id: uuid.UUID,
        name: str,
        environment_name: str,
        mount_path: str,
        source_type: str,
        source_name: Optional[str] = None,
        sub_paths: Optional[List[str]] = None,
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
            source_config=source_config,
            sub_paths=sub_paths or [],
            tenant_id=tenant_id,
        )


def check_storage_class_exists(application: Application, storage_class_name: str) -> bool:
    """检查给定的 StorageClass 是否存在于 Kubernetes 集群中。

    :param application: Application object
    :param storage_class_name: 要检查的 StorageClass 的名称。
    :return bool: 如果 StorageClass 存在,返回 True。否则返回 False。
    """
    cluster = get_app_prod_env_cluster(application)
    with get_client_by_cluster_name(cluster_name=cluster.name) as client:
        storage_class_client = KStorageClass(client)
        try:
            _ = storage_class_client.get(name=storage_class_name)
        except ResourceMissing:
            return False
        else:
            return True


def check_persistent_storage_enabled(application: Application) -> bool:
    """判断应用是否支持持久存储特性"""
    # 若应用没有开启持久存储应用特性, 则不支持
    if not ApplicationFeatureFlag.objects.has_feature(AppFeatureFlag.ENABLE_PERSISTENT_STORAGE, application):
        return False
    # 若集群不支持配置的 StorageClass, 则不支持
    return check_storage_class_exists(
        application=application, storage_class_name=settings.DEFAULT_PERSISTENT_STORAGE_CLASS_NAME
    )
