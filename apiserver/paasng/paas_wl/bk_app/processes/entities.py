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
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from paas_wl.workloads.release_controller.constants import ImagePullPolicy


@dataclass
class Resources:
    """计算资源定义"""

    @dataclass
    class Spec:
        cpu: str
        memory: str

    limits: Optional[Spec] = None
    requests: Optional[Spec] = None


@dataclass
class Runtime:
    """运行相关"""

    envs: Dict[str, str]
    image: str
    # 实际的镜像启动命令
    command: List[str]
    args: List[str]
    # 由于 command/args 本身经过了镜像启动脚本的封装
    # 所以这里我们额外存储一个用户填写的启动命令
    # 假设 procfile 中是 `web: python manage.py runserver`
    # 则 command: ['bash', '/runner/init']
    #    args: ["start", "web"]
    #    proc_command: "python manage.py runserver"
    proc_command: str = ""
    image_pull_policy: ImagePullPolicy = field(default=ImagePullPolicy.IF_NOT_PRESENT)
    image_pull_secrets: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Probe:
    type: str = "common"
    params: dict = field(default_factory=dict)


@dataclass
class Status:
    replicas: int
    success: int = 0
    failed: int = 0

    version: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {'replicas': self.replicas, 'success': self.success, 'failed': self.failed}
