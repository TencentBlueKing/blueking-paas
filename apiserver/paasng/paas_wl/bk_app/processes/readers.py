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

from typing import Dict, List, Optional, cast

from django.core.exceptions import ObjectDoesNotExist
from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.constants import (
    BKAPP_CODE_ANNO_KEY,
    ENVIRONMENT_ANNO_KEY,
    MODULE_NAME_ANNO_KEY,
    RESOURCE_TYPE_KEY,
    WLAPP_NAME_ANNO_KEY,
)
from paas_wl.bk_app.processes.kres_entities import Instance, Process
from paas_wl.core.resource import get_process_selector
from paas_wl.infras.resources.base.exceptions import NotAppScopedResource
from paas_wl.infras.resources.base.kres import KPod
from paas_wl.infras.resources.kube_res.base import AppEntityReader, NamespaceScopedReader, ResourceList
from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paasng.platform.applications.models import ModuleEnvironment


class ProcessAPIAdapter:
    """Data adapter for Process"""

    @staticmethod
    def app_selector(app: "WlApp") -> Dict[str, str]:
        """Return labels selector dict, useful for filter Process/Instance from k8s"""
        # TODO: 使用 resource-type/category 来过滤
        if app.type == WlAppType.CLOUD_NATIVE:
            return {MODULE_NAME_ANNO_KEY: app.module_name}
        # return {"module_name": app.module_name}
        return {}

    @staticmethod
    def type_selector() -> Dict[str, str]:
        """Return labels selector dict, useful for filter Process/Instance from k8s"""
        return {RESOURCE_TYPE_KEY: "process"}


class ProcessReader(AppEntityReader[Process, WlApp]):
    """Manager for ProcSpecs"""

    def list_by_app_with_meta(
        self, app: "WlApp", labels: Optional[Dict] = None, fields: Optional[Dict] = None
    ) -> ResourceList[Process]:
        labels = labels or {}
        extra_labels = ProcessAPIAdapter.app_selector(app)
        labels.update(extra_labels)
        return super().list_by_app_with_meta(app, labels)

    def get_by_type(self, app: "WlApp", type: str) -> "Process":
        """Get object by process type"""
        labels = get_process_selector(app, type)
        objs = self.list_by_app(app, labels=labels)
        if objs:
            return objs[0]
        raise AppEntityNotFound(f"No processes can be found with type={type}")


process_kmodel = ProcessReader(Process)


class InstanceReader(AppEntityReader[Instance, WlApp]):
    """Customized reader for ProcInstance"""

    def list_by_process_type(self, app: "WlApp", process_type: str) -> List[Instance]:
        """List instances by process type"""
        labels = get_process_selector(app, process_type)
        return self.list_by_app(app, labels=labels)

    def list_by_app_with_meta(
        self, app: "WlApp", labels: Optional[Dict] = None, fields: Optional[Dict] = None
    ) -> ResourceList[Instance]:
        labels = labels or {}
        extra_labels = ProcessAPIAdapter.app_selector(app)
        labels.update(extra_labels)
        res = super().list_by_app_with_meta(app, labels)
        if app.type == WlAppType.DEFAULT:
            # Ignore instances with no valid "release_version" label
            # TODO: 云原生应用也需要添加 version 相关的字段
            res.items = [i for i in res.items if i.version > 0]
        return res

    def get_logs(self, obj: Instance, tail_lines: Optional[int] = None, **kwargs):
        """Get logs from kubernetes api"""
        with self.kres(obj.app) as kres_client:
            kres_client = cast(KPod, kres_client)
            return kres_client.get_log(
                name=obj.name,
                namespace=obj.app.namespace,
                tail_lines=tail_lines,
                container=obj.app.scheduler_safe_name,
                **kwargs,
            )


instance_kmodel = InstanceReader(Instance)


def retrieve_associated_wl_app(labels: Dict[str, str]) -> WlApp:
    if wl_app_name := labels.get(WLAPP_NAME_ANNO_KEY):
        try:
            return WlApp.objects.get(name=wl_app_name)
        except ObjectDoesNotExist:
            raise NotAppScopedResource

    # 兜底, 根据 app code, module name, environment 查询 wl_app
    app_code = labels.get(BKAPP_CODE_ANNO_KEY)
    module_name = labels.get(MODULE_NAME_ANNO_KEY)
    environment = labels.get(ENVIRONMENT_ANNO_KEY)

    if not app_code or not module_name or not environment:
        raise NotAppScopedResource
    try:
        return ModuleEnvironment.objects.get(
            application__code=app_code, module__name=module_name, environment=environment
        ).wl_app
    except ObjectDoesNotExist:
        raise NotAppScopedResource


class ProcessNamespaceScopedReader(NamespaceScopedReader[Process, WlApp]):
    entity_type = Process

    def list_by_ns_with_mdata(
        self, cluster_name: str, namespace: str, labels: Optional[Dict] = None
    ) -> ResourceList[Process]:
        labels = labels or {}
        extra_labels = ProcessAPIAdapter.type_selector()
        labels.update(extra_labels)
        return super().list_by_ns_with_mdata(cluster_name, namespace, labels)

    def retrieve_associated_kres_app(self, kube_data: ResourceInstance) -> WlApp:
        labels: Dict[str, str] = kube_data.metadata.labels or {}
        return retrieve_associated_wl_app(labels)


class InstanceNamespaceScopeReader(NamespaceScopedReader[Instance, WlApp]):
    entity_type = Instance

    def list_by_ns_with_mdata(
        self, cluster_name: str, namespace: str, labels: Optional[Dict] = None
    ) -> ResourceList[Instance]:
        labels = labels or {}
        extra_labels = ProcessAPIAdapter.type_selector()
        labels.update(extra_labels)
        return super().list_by_ns_with_mdata(cluster_name, namespace, labels)

    def retrieve_associated_kres_app(self, kube_data: ResourceInstance) -> WlApp:
        labels: Dict[str, str] = kube_data.metadata.labels or {}
        return retrieve_associated_wl_app(labels)


ns_process_kmodel = ProcessNamespaceScopedReader()
ns_instance_kmodel = InstanceNamespaceScopeReader()
