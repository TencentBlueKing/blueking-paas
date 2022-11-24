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
from dataclasses import dataclass
from typing import Iterable, Optional

from paas_wl.platform.applications.models import App
from paas_wl.platform.applications.models.release import Release

from .models import Process

logger = logging.getLogger(__name__)


@dataclass
class AppProcessManager:
    """
    从 App 维度操作 Process
    """

    app: 'App'

    def assemble_process(
        self, process_type: str, release: Optional['Release'] = None, extra_envs: Optional[dict] = None
    ) -> Process:
        """通过 Release 对象组装单个 Process 对象"""
        if not release:
            release = Release.objects.get_latest(self.app)

        return Process.from_release(process_type, release, extra_envs)

    def assemble_processes(
        self, release: Optional['Release'] = None, extra_envs: Optional[dict] = None
    ) -> Iterable[Process]:
        """通过 Release 对象组装 App 所有 Process 对象"""
        if not release:
            release = Release.objects.get_latest(self.app)

        for process_type in release.get_procfile().keys():
            yield self.assemble_process(process_type, release, extra_envs)
