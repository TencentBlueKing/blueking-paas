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
"""Archive related deploy functions"""
import logging
from typing import Optional

from paas_wl.monitoring.app_monitor.managers import make_bk_monitor_controller
from paas_wl.platform.applications.models import Release
from paas_wl.workloads.processes.controllers import get_proc_mgr
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class ArchiveOperationController:
    """Controller for offline operation"""

    def __init__(self, env: ModuleEnvironment, operation_id: Optional[str] = None):
        self.operation_id = operation_id
        self.env = env

    def start(self):
        self.stop_all_processes()
        make_bk_monitor_controller(self.env.wl_app).remove()

    def stop_all_processes(self):
        """Stop all processes"""
        ctl = get_proc_mgr(env=self.env)
        release = Release.objects.get_latest(self.env.wl_app)
        for proc_type in release.get_procfile().keys():
            ctl.stop(proc_type=proc_type)
