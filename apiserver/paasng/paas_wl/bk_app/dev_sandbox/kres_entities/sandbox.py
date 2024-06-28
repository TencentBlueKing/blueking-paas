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

from dataclasses import dataclass
from typing import Optional

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.dev_sandbox.entities import Resources, Runtime, Status
from paas_wl.bk_app.dev_sandbox.kres_slzs import DevSandboxDeserializer, DevSandboxSerializer
from paas_wl.infras.resources.base import kres
from paas_wl.infras.resources.kube_res.base import AppEntity


@dataclass
class DevSandbox(AppEntity):
    """DevSandbox entity"""

    runtime: Runtime
    resources: Optional[Resources] = None
    # 部署后, 从集群中获取状态
    status: Optional[Status] = None

    class Meta:
        kres_class = kres.KDeployment
        serializer = DevSandboxSerializer
        deserializer = DevSandboxDeserializer

    @classmethod
    def create(cls, dev_wl_app: WlApp, runtime: Runtime, resources: Optional[Resources] = None) -> "DevSandbox":
        return cls(app=dev_wl_app, name=get_dev_sandbox_name(dev_wl_app), runtime=runtime, resources=resources)


def get_dev_sandbox_name(dev_wl_app: WlApp) -> str:
    return dev_wl_app.scheduler_safe_name
