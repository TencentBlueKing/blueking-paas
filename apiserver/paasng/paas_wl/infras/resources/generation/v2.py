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
from paas_wl.bk_app.cnative.specs.constants import (
    BKAPP_CODE_ANNO_KEY,
    ENVIRONMENT_ANNO_KEY,
    MODULE_NAME_ANNO_KEY,
    RESOURCE_TYPE_KEY,
    WLAPP_NAME_ANNO_KEY,
)
from paas_wl.utils.basic import digest_if_length_exceeded

from .mapper import MapperPack, ResourceIdentifiers


class V2ProcResIdentifiers(ResourceIdentifiers):
    """Resource identifiers for process, v2"""

    @property
    def deployment_name(self) -> str:
        """The name of deployment."""
        return f"{self.proc_config.app.scheduler_safe_name}--{self.proc_config.type}"

    @property
    def pod_name(self) -> str:
        """The name of pod."""
        return f"{self.proc_config.app.scheduler_safe_name}--{self.proc_config.type}"

    @property
    def match_labels(self) -> dict:
        return {"pod_selector": self.pod_selector}

    @property
    def pod_selector(self) -> str:
        return digest_if_length_exceeded(f"{self.proc_config.app.name}-{self.proc_config.type}", 63)

    @property
    def labels(self) -> dict:
        mdata = get_metadata(self.proc_config.app)
        return {
            "pod_selector": self.pod_selector,
            "release_version": str(self.proc_config.version),
            "region": self.proc_config.app.region,
            "app_code": mdata.get_paas_app_code(),
            "module_name": mdata.module_name,
            "env": mdata.environment,
            "process_id": self.proc_config.type,
            "category": "bkapp",
            "mapper_version": "v2",
            # 云原生应用新增的 labels
            BKAPP_CODE_ANNO_KEY: mdata.get_paas_app_code(),
            MODULE_NAME_ANNO_KEY: mdata.module_name,
            ENVIRONMENT_ANNO_KEY: mdata.environment,
            WLAPP_NAME_ANNO_KEY: self.proc_config.app.name,
            RESOURCE_TYPE_KEY: "process",
        }


class V2Mapper(MapperPack):
    version = "v2"
    proc_resources = V2ProcResIdentifiers
