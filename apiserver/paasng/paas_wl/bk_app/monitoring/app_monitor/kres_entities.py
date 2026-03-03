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

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from paas_wl.infras.resources.base.crd import KServiceMonitor
from paas_wl.infras.resources.kube_res.base import AppEntity, AppEntityManager

from .entities import Endpoint, ServiceSelector
from .kres_slzs import ServiceMonitorDeserializer, ServiceMonitorSerializer

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp

logger = logging.getLogger(__name__)


@dataclass
class ServiceMonitor(AppEntity):
    """ServiceMonitor 通过 selector 过滤需要监控的 Service, 并通过访问 endpoint 描述的端口进行数据采集"""

    endpoint: Endpoint
    selector: ServiceSelector
    match_namespaces: List[str]

    class Meta:
        kres_class = KServiceMonitor
        deserializer = ServiceMonitorDeserializer
        serializer = ServiceMonitorSerializer


service_monitor_kmodel: "AppEntityManager[ServiceMonitor, WlApp]" = AppEntityManager(ServiceMonitor)
