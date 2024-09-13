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

from typing import Literal, Optional, Union

from django.conf import settings
from pydantic import BaseModel

from paasng.platform.bkapp_model.constants import PORT_PLACEHOLDER, ExposedTypeName
from paasng.utils.structure import prepare_json_field


class ExposedType(BaseModel):
    """ExposedType is the exposed type of the ProcService

    :param name: name of the exposed type. Default is bk/http
    """

    name: Literal[ExposedTypeName.BK_HTTP] = ExposedTypeName.BK_HTTP


@prepare_json_field
class ProcService(BaseModel):
    """
    ProcService is a process service which used to expose network

    :param name: service name
    :param target_port: number of the port to access on the pods(container) targeted by the service.
        it can be set to a string, but it is restricted to the value "${PORT}" only
    :param protocol: protocol of the service. Default is TCP
    :param exposed_type: exposed type of the service. If not specified, the service can only be accessed within the
        cluster, not from outside
    :param port: number of the port that will be exposed by this service
    """

    name: str
    target_port: Union[int, str]
    protocol: Literal["TCP", "UDP"] = "TCP"
    exposed_type: Optional[ExposedType] = None
    port: Optional[int] = None

    def render_port(self):
        """render target_port to settings.CONTAINER_PORT if original value is ${PORT}"""
        if self.target_port == PORT_PLACEHOLDER:
            self.target_port = settings.CONTAINER_PORT
        return self
