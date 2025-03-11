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

from typing import List, Literal, Optional, Union

from django.conf import settings
from pydantic import BaseModel, Field

from paasng.platform.bkapp_model.constants import PORT_PLACEHOLDER
from paasng.utils.structure import prepare_json_field


class ExecAction(BaseModel):
    command: List[str]


class HTTPHeader(BaseModel):
    name: str
    value: str


class HTTPGetAction(BaseModel):
    port: Union[int, str]
    host: Optional[str] = None
    path: Optional[str] = None
    http_headers: List[HTTPHeader] = Field(default_factory=list)
    scheme: Optional[Literal["HTTP", "HTTPS"]] = None


class TCPSocketAction(BaseModel):
    port: Union[int, str]
    host: Optional[str] = None


@prepare_json_field
class ProbeHandler(BaseModel):
    exec: Optional[ExecAction] = None
    http_get: Optional[HTTPGetAction] = None
    tcp_socket: Optional[TCPSocketAction] = None


@prepare_json_field
class Probe(BaseModel):
    """
    健康探针

    :param exec: 命令行执行探测
    :param http_get: http 探测
    :param tcp_socket: tcp 探测
    :param initial_delay_seconds: 容器启动后要等待多少秒后才启动探测. 默认为 0
    :param timeout_seconds: 探测的超时后等待多少秒。默认值是 1 秒
    :param period_seconds: 探测的间隔时间。默认值是 10 秒
    :param success_threshold: 探针在失败后，被视为成功的最小连续成功数。默认值是 1
    :param failure_threshold: 探针连续失败了多少次后，认为探测失败。默认值是 3
    """

    exec: Optional[ExecAction] = None
    http_get: Optional[HTTPGetAction] = None
    tcp_socket: Optional[TCPSocketAction] = None

    initial_delay_seconds: Optional[int] = 0
    timeout_seconds: Optional[int] = 1
    period_seconds: Optional[int] = 10
    success_threshold: Optional[int] = 1
    failure_threshold: Optional[int] = 3

    def render_port(self):
        """render target_port to settings.CONTAINER_PORT if original value is ${PORT}"""
        if self.tcp_socket and self.tcp_socket.port == PORT_PLACEHOLDER:
            self.tcp_socket.port = settings.CONTAINER_PORT

        if self.http_get and self.http_get.port == PORT_PLACEHOLDER:
            self.http_get.port = settings.CONTAINER_PORT

        return self


@prepare_json_field
class ProbeSet(BaseModel):
    """
    健康探针集

    :param liveness: 存活探针
    :param readiness: 就绪探针
    :param startup: 启动探针
    """

    liveness: Optional[Probe] = None
    readiness: Optional[Probe] = None
    startup: Optional[Probe] = None

    def render_port(self):
        """render port to settings.CONTAINER_PORT if original value is ${PORT}"""
        if self.liveness:
            self.liveness = self.liveness.render_port()
        if self.startup:
            self.startup = self.startup.render_port()
        if self.readiness:
            self.readiness = self.readiness.render_port()

        return self
