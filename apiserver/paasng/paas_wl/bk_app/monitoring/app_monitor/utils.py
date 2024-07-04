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

from typing import Optional

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.monitoring.app_monitor import constants
from paas_wl.bk_app.monitoring.app_monitor.models import AppMetricsMonitor
from paas_wl.workloads.networking.ingress.entities import PServicePortPair


def build_monitor_port(app: WlApp) -> Optional[PServicePortPair]:
    """Generate the build-in metrics port objects"""
    try:
        monitor = AppMetricsMonitor.objects.get(app=app)
    except AppMetricsMonitor.DoesNotExist:
        return None

    return PServicePortPair(
        name=constants.METRICS_PORT_NAME,
        port=monitor.port,
        target_port=monitor.target_port,
        protocol=constants.METRICS_PORT_PROTOCOL,
    )
