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
from typing import TYPE_CHECKING, Dict, List, Optional, cast

from paas_wl.cnative.specs.constants import MODULE_NAME_ANNO_KEY
from paas_wl.platform.applications.constants import WlAppType
from paas_wl.platform.applications.models.managers.app_res_ver import AppResVerManager
from paas_wl.resources.base.kres import KPod
from paas_wl.resources.kube_res.base import AppEntityReader, ResourceList
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.processes.constants import PROCESS_NAME_KEY
from paas_wl.workloads.processes.entities import Instance, Process
from paas_wl.workloads.processes.managers import AppProcessManager

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import WlApp


class ProcessAPIAdapter:
    """Data adapter for Process"""

    @staticmethod
    def process_selector(app: 'WlApp', process_type: str) -> Dict[str, str]:
        """Return pod selector dict, useful for construct Deployment body and related Service"""
        # TODO: 由于云原生应用对命名空间进行合并（仅保留 stag/prod 两个命名空间），因此查询进程信息，需要带上模块信息的 labels
        if app.type == WlAppType.CLOUD_NATIVE:
            return {MODULE_NAME_ANNO_KEY: app.module_name, PROCESS_NAME_KEY: process_type}

        proc = AppProcessManager(app).assemble_process(process_type)
        return {"pod_selector": AppResVerManager(app).curr_version.deployment(proc).pod_selector}

    @staticmethod
    def app_selector(app: 'WlApp') -> Dict[str, str]:
        """Return pod selector dict, useful for filter Process/Instance from k8s"""
        # TODO: 使用 resource-type/category 来过滤
        if app.type == WlAppType.CLOUD_NATIVE:
            return {MODULE_NAME_ANNO_KEY: app.module_name}
        # return {"module_name": app.module_name}
        return {}


class ProcessReader(AppEntityReader[Process]):
    """Manager for ProcSpecs"""

    def list_by_app_with_meta(self, app: 'WlApp', labels: Optional[Dict] = None) -> ResourceList[Process]:
        labels = labels or {}
        extra_labels = ProcessAPIAdapter.app_selector(app)
        labels.update(extra_labels)
        return super().list_by_app_with_meta(app, labels)

    def get_by_type(self, app: 'WlApp', type: str) -> 'Process':
        """Get object by process type"""
        labels = ProcessAPIAdapter.process_selector(app, type)
        objs = self.list_by_app(app, labels=labels)
        if objs:
            return objs[0]
        raise AppEntityNotFound(f'No processes can be found with type={type}')


process_kmodel = ProcessReader(Process)


class InstanceReader(AppEntityReader[Instance]):
    """Customized reader for ProcInstance"""

    def list_by_process_type(self, app: 'WlApp', process_type: str) -> List[Instance]:
        """List instances by process type"""
        labels = ProcessAPIAdapter.process_selector(app, process_type)
        return self.list_by_app(app, labels=labels)

    def list_by_app_with_meta(self, app: 'WlApp', labels: Optional[Dict] = None) -> ResourceList[Instance]:
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
