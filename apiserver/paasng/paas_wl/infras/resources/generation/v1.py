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
from paas_wl.bk_app.applications.managers import get_metadata
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.cnative.specs.constants import (
    BKAPP_CODE_ANNO_KEY,
    ENVIRONMENT_ANNO_KEY,
    MODULE_NAME_ANNO_KEY,
    RESOURCE_TYPE_KEY,
    WLAPP_NAME_ANNO_KEY,
)

from .mapper import MapperPack, ResourceIdentifiers


def v1_scheduler_safe_name(app: WlApp):
    """the legacy app name in scheduler backend
    diff with version v2 scheduler_safe_name(current version) , version v1 have `region` as prefix"""
    return f"{app.region}-{app.scheduler_safe_name}"


class V1ProcResIdentifiers(ResourceIdentifiers):
    """Resource identifiers for process, v1"""

    @property
    def deployment_name(self) -> str:
        """The name of deployment."""
        return (
            f"{v1_scheduler_safe_name(self.proc_config.app)}-{self.proc_config.type}-"
            f"{self.proc_config.command_name}-deployment"
        )

    @property
    def pod_name(self) -> str:
        """The name of pod."""
        return (
            f"{v1_scheduler_safe_name(self.proc_config.app)}-{self.proc_config.type}-"
            f"{self.proc_config.command_name}-deployment"
        )

    @property
    def match_labels(self) -> dict:
        return {"pod_selector": self.pod_selector}

    @property
    def pod_selector(self) -> str:
        return f"{v1_scheduler_safe_name(self.proc_config.app)}-{self.proc_config.type}-deployment"

    @property
    def labels(self) -> dict:
        mdata = get_metadata(self.proc_config.app)
        # module_name 将作为日志采集的标识 label，拥有 module_name 的 pod ，app_code 将是
        # paasng_app_code，而没有 module_name 的 pod，则是 engine_app.name
        # 理论上，这里的 app_code 就应该是 paasng_app_code，label 中尽量将信息拆散，由上层组装
        return {
            "pod_selector": self.pod_selector,
            "release_version": str(self.proc_config.version),
            "region": self.proc_config.app.region,
            "app_code": mdata.get_paas_app_code(),
            "module_name": mdata.module_name,
            "env": mdata.environment,
            "process_id": self.proc_config.type,
            # mark deployment as bkapp, maybe we will have other category in the future.
            "category": "bkapp",
            "mapper_version": "v1",
            # 云原生应用新增的 labels
            BKAPP_CODE_ANNO_KEY: mdata.get_paas_app_code(),
            MODULE_NAME_ANNO_KEY: mdata.module_name,
            ENVIRONMENT_ANNO_KEY: mdata.environment,
            WLAPP_NAME_ANNO_KEY: self.proc_config.app.name,
            RESOURCE_TYPE_KEY: "process",
        }


class V1Mapper(MapperPack):
    version = "v1"
    proc_resources = V1ProcResIdentifiers
