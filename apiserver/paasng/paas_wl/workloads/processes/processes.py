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
from typing import Dict, List, Optional

from attrs import define

logger = logging.getLogger(__name__)


@define
class Instance:
    """A Process instance object
    TODO: 与 PlainInstance 统一
    """

    name: str
    host_ip: str
    start_time: str
    state: str
    ready: bool
    image: str
    restart_count: int
    version: int
    process_type: Optional[str] = None
    namespace: Optional[str] = None

    def __str__(self):
        return f'Instance<{self.name}-{self.state}>'


@define
class Process:
    """
    Q: What's the differences between Process and ProcessSpec?
    A: Process represents the actual data from engine backend, and ProcessSpec represents the expectation of user.
    TODO: 与 PlainProcess 统一
    """

    type: str
    version: int
    command: str
    process_status: Dict
    desired_replicas: str
    instances: List[Instance]

    @property
    def available_instance_count(self):
        return len([instance for instance in self.instances if instance.ready and instance.version == self.version])

    def __repr__(self):
        return f'Process<{self.type}>'
