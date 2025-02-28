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

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from paas_wl.workloads.release_controller.constants import ImagePullPolicy
from paasng.utils.structure import prepare_json_field


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
class Status:
    replicas: int
    success: int = 0
    failed: int = 0

    version: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {"replicas": self.replicas, "success": self.success, "failed": self.failed}


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


@prepare_json_field
class ProbeSet(BaseModel):
    """
    健康探针集
    暂时与 from paasng.platform.bkapp_model.entities import ProbeSet 的字段冗余
    但是他们的职责不同，paasng 侧的负责记录描述文件中的探针配置
    paas_wl 侧的为了映射 process entity --> k8s deployment

    :param liveness: 存活探针
    :param readiness: 就绪探针
    :param startup: 启动探针
    """

    liveness: Optional[Probe] = None
    readiness: Optional[Probe] = None
    startup: Optional[Probe] = None
