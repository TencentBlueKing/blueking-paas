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

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PlanSchema(BaseModel):
    """RabbitMQ 服务配置"""

    host: Optional[str] = Field(None, description="RabbitMQ 服务器主机地址", example="rabbitmq.example.com")
    port: Optional[int] = Field(None, description="RabbitMQ 服务端口号", example=5672)
    management_api: Optional[str] = Field(
        None, description="RabbitMQ 管理API地址", example="http://rabbitmq.example.com:15672"
    )
    admin: Optional[str] = Field(None, description="RabbitMQ 管理员用户名", example="admin")
    password: Optional[str] = Field(None, description="RabbitMQ 管理员密码", example="password123")
    version: Optional[str] = Field(None, description="RabbitMQ 服务版本", example="3.9.5")
    tls: Dict[str, str] = Field(
        default_factory=dict, description="TLS 配置参数", example={"ca_cert": "/path/to/ca.pem", "verify": "true"}
    )
    clusters: List[Dict] = Field(
        default_factory=list,
        description="RabbitMQ 集群配置列表",
        example=[{"host": "node1.example.com", "port": 5672}],
    )
