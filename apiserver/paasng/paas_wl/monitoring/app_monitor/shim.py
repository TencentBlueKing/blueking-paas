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
import logging

from django.conf import settings

from paas_wl.monitoring.app_monitor.managers import AppMonitorController, NullController
from paas_wl.monitoring.app_monitor.models import AppMetricsMonitor
from paas_wl.platform.applications.models import WlApp
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


def make_bk_monitor_controller(app: WlApp):
    if not settings.ENABLE_BK_MONITOR:
        logger.warning("BKMonitor is not ready, skip apply ServiceMonitor")
        return NullController()
    else:
        return AppMonitorController(app)


def upsert_app_monitor(
    env: ModuleEnvironment,
    port: int,
    target_port: int,
):
    """更新或创建蓝鲸监控相关资源(ServiceMonitor)的配置

    - AppMetricsMonitor 创建后需要在应用部署时才会真正下发到 k8s 集群
    """
    instance, _ = AppMetricsMonitor.objects.update_or_create(
        defaults={
            "port": port,
            "target_port": target_port,
            "is_enabled": True,
        },
        app=env.wl_app,
    )
