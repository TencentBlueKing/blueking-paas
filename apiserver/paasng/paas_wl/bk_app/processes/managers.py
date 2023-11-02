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

from paas_wl.bk_app.applications.models import Release, WlApp

from .entities import Process

logger = logging.getLogger(__name__)


@dataclass
class AppProcessManager:
    """从 WlApp 维度操作 Process"""

    app: 'WlApp'

    def assemble_process(
        self, process_type: str, release: Optional['Release'] = None, extra_envs: Optional[dict] = None
    ) -> Process:
        """通过 Release 对象组装单个 Process 对象"""
        # WARNING: 当 extra_envs 参数为 None 时，我们无法通过单纯的 release 对象来构造
        # 有效可运行的 Process 进程，因为缺少必须的环境变量。这种情况下，平台只能从 release
        # 所绑定的 build 对象中获取少数几个构建用环境变量（参考 Release.get_envs()），
        # 其他的内置环境变量都拿不到。
        #
        # 当前除了在普通应用部署结束时，由调用方手动传入了 extra_envs 参数（其中包含正常运
        # 行所需的环境变量）的情况外，其他调用均未提供有效的 `extra_envs`，所产生的 Process
        # 对象也无法直接被部署到集群中。
        #
        # 进程启停、扩缩容等操作因为用了 PATCH 方法来修改 Deployment 资源，不涉及 Process
        # 组装过程，不受影响。
        #
        # TODO: 未来考虑是否需要把 extra_envs 中的所有环境变量保存到 Build 中，从而保证
        # 可以通过 Release 对象还原构造出有效的 Process 对象。
        if not release:
            release = Release.objects.get_latest(self.app)

        return Process.from_release(process_type, release, extra_envs)

    def assemble_processes(
        self, release: Optional['Release'] = None, extra_envs: Optional[dict] = None
    ) -> Iterable[Process]:
        """通过 Release 对象组装 WlApp 所有 Process 对象"""
        if not release:
            release = Release.objects.get_latest(self.app)

        for process_type in release.get_procfile().keys():
            yield self.assemble_process(process_type, release, extra_envs)
