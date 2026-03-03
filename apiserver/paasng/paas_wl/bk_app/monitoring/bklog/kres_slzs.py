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

from dataclasses import asdict
from typing import TYPE_CHECKING, Dict, List, Optional

import cattrs
from kubernetes.dynamic import ResourceInstance

from paas_wl.bk_app.applications.managers import get_metadata
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.monitoring.bklog import constants
from paas_wl.bk_app.monitoring.bklog.entities import LabelSelector, LogFilterCondition
from paas_wl.infras.resources.kube_res.base import AppEntityDeserializer, AppEntitySerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.monitoring.bklog.kres_entities import BkAppLogConfig


class BKLogConfigSerializer(AppEntitySerializer["BkAppLogConfig"]):
    api_version = "bk.tencent.com/v1alpha1"

    def serialize(self, obj: "BkAppLogConfig", original_obj: Optional[ResourceInstance] = None, **kwargs) -> Dict:
        wl_app_metadata = get_metadata(obj.app)
        metadata = {
            "name": obj.name,
            "namespace": obj.app.namespace,
            "labels": {
                "app.kubernetes.io/managed-by": "bk-paas3",
                constants.BKAPP_CODE_ANNO_KEY: wl_app_metadata.get_paas_app_code(),
                constants.MODULE_NAME_ANNO_KEY: wl_app_metadata.module_name,
                constants.ENVIRONMENT_ANNO_KEY: wl_app_metadata.environment,
                constants.WLAPP_NAME_ANNO_KEY: obj.app.name,
            },
        }
        spec = {
            "addPodLabel": True,
            "namespaceSelector": {
                "matchNames": [obj.app.namespace],
            },
            # allContainer 指的是采集命名空间下的所有 Pod, 并非 Pod 中的 container
            # 当 allContainer = True 时, `workloadType` 和 `labelSelector` 不再生效
            "allContainer": False,
            "workloadType": obj.workload_type,
            "labelSelector": asdict(obj.label_selector),
            "dataId": obj.data_id,
            "encoding": obj.encoding,
            "path": obj.paths,
            "filters": asdict(obj.filters) if obj.filters else [],
            "extMeta": obj.ext_meta,
            "logConfigType": obj.config_type.value,
        }
        return {
            "metadata": metadata,
            "spec": spec,
            "apiVersion": self.get_apiversion(),
            "kind": obj.Meta.kres_class.kind,
        }


class BKLogConfigDeserializer(AppEntityDeserializer["BkAppLogConfig", "WlApp"]):
    api_version = "bk.tencent.com/v1alpha1"

    def deserialize(self, app: WlApp, kube_data: ResourceInstance) -> "BkAppLogConfig":
        spec = kube_data.spec
        config = self.entity_type(
            app=app,
            name=kube_data.metadata.name,
            data_id=spec.dataId,
            encoding=spec.encoding,
            paths=spec.path,
            filters=cattrs.structure(spec.filters, List[LogFilterCondition]) if hasattr(spec, "filters") else [],
            ext_meta=spec.extMeta,
            config_type=spec.logConfigType,
            workload_type=spec.workloadType,
            label_selector=cattrs.structure(spec.labelSelector, LabelSelector),
        )
        config._kube_data = kube_data
        return config
