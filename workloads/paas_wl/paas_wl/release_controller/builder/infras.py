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
from typing import ClassVar

from paas_wl.release_controller.builder.constants import DeployEventStatus
from paas_wl.release_controller.entities import Runtime
from paas_wl.resources.kube_res.base import Schedule
from paas_wl.utils.stream import ConsoleStream, Stream

logger = logging.getLogger(__name__)


@dataclass
class SlugBuilderTemplate:
    """The Template to run the slug-builder Pod
    :param name: the name of the Pod
    :param namespace: the namespace of the Pod
    :param runtime: Runtime Info of the Pod, including image, pullSecrets, command, args and so on.
    :param schedule: Schedule Rule of the Pod, including tolerations and node_selector.
    """

    name: str
    namespace: str
    runtime: Runtime
    schedule: Schedule


class BuildProcedure:
    """A application build procedure wrapper, be used to ignore exception raised in build process

    :param stream: stream for writing title and messages
    """

    DEFAULT_TITLE_PREFIX: str = '正在'
    INTERNAL_EVENT_TYPE: str = "step"

    def __init__(self, stream: Stream, title: str, prefix=None, write_to_console: bool = False):
        self.stream = ConsoleStream() if write_to_console else stream
        self.title = title
        self.prefix = prefix or self.DEFAULT_TITLE_PREFIX

    def __enter__(self):
        self.stream.write_title(f'{self.prefix}{self.title}')
        self.write_stream_event(self.title, DeployEventStatus.STARTED)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.write_stream_event(self.title, DeployEventStatus.FINISHED)
            return True

        # TODO: allow exception `BuildProcessShouldAbortError` to be outputted directly into the stream,
        # While other exceptions should be masked as "Unknown error" instead for better user
        # experience.
        msg = f"步骤 [{self.title}] 出错了，请稍候重试。"
        self.stream.write_message(msg)

        self.write_stream_event(self.title, DeployEventStatus.ABORTED)
        return False

    def write_stream_event(self, name: str, status: DeployEventStatus):
        """向 stream 中写入内部交互事件"""
        self.stream.write_event(
            **InternalEvent(name=name, type=self.INTERNAL_EVENT_TYPE, status=status).to_stream_event()
        )


@dataclass
class InternalEvent:
    EVENT_NAME: ClassVar[str] = "internal"
    PUBLISHER: ClassVar[str] = "engine"

    name: str
    type: str
    status: DeployEventStatus

    def to_stream_event(self) -> dict:
        return dict(
            event_name=self.EVENT_NAME,
            data=dict(name=self.name, type=self.type, status=self.status.value, publisher=self.PUBLISHER),
        )
