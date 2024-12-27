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

from typing import List, Optional

from pydantic.main import BaseModel


# Plan Schema
class BaseConfigSchema(BaseModel):
    """The base schema for all types of configurations"""


class RabbitMQConfigSchema(BaseConfigSchema):
    host: str
    port: int
    user: str
    password: str
    http_port: int


class MySQLConfigSchema(BaseConfigSchema):
    host: str
    port: int
    user: str
    password: str
    auth_ip_list: List[str]


class GCSMySQLServerValue(BaseModel):
    host: str
    port: int


class GCSMySQLServer(BaseModel):
    values: GCSMySQLServerValue
    weight: int


class GCSMySQLConfigSchema(BaseConfigSchema):
    host: Optional[str]
    port: Optional[int]
    auth_ip_list: List[str]
    servers: List[GCSMySQLServer] = []


class APMConfigSchema(BaseConfigSchema):
    service_name: str
    service_port: str
    app: str
    token: str
    domain: str


class SentryConfigSchema(BaseConfigSchema):
    organization: str
    service_name: str
    service_port: int
    token: str
    domain: str


class ResourcePoolConfigSchema(BaseConfigSchema):
    recyclable: bool


# Instance Schema
class APMInstanceSchema(BaseModel):
    id: str
    token: str
    DATADOG_TRACE_AGENT_HOSTNAME: str
    DATADOG_TRACE_AGENT_PORT: int
    DD_TRACE_SAMPLE_RATE: float


class MySQLInstanceSchema(BaseModel):
    name: str
    host: str
    port: int
    user: str
    password: str


class RedisInstanceSchema(BaseModel):
    host: str
    port: int
    password: str


class SentryInstanceSchema(BaseModel):
    dsn: str


class RabbitMQInstanceSchema(BaseModel):
    host: str
    port: int
    user: str
    vhost: str
    password: str
