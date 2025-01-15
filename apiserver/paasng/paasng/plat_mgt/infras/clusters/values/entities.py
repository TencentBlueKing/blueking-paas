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

"""
entities 用于存放 Helm Charts 对应的 Values（仅特殊指定部分，非存量）的模型定义
"""

from typing import Dict

from django.conf import settings
from pydantic import BaseModel, Field


class ImageConfig(BaseModel):
    registry: str = settings.CLUSTER_COMPONENT_IMAGE_REGISTRY


class NodePortsConfig(BaseModel):
    http: int = 30180
    https: int = 30543


class IngressServiceConfig(BaseModel):
    nodePorts: NodePortsConfig = Field(default_factory=NodePortsConfig)


class BkIngressNginxValues(BaseModel):
    hostNetwork: bool
    image: ImageConfig
    service: IngressServiceConfig
    nodeSelector: Dict[str, str] = Field(default_factory=dict)


class BkAppLogCollectionGlobalValues(BaseModel):
    elasticSearchHost: str
    elasticSearchPassword: str
    elasticSearchPort: int
    elasticSearchSchema: str
    elasticSearchUsername: str


class BkAppFilebeatValues(BaseModel):
    image: ImageConfig
    containersLogPath: str


class BkAppLogstashValues(BaseModel):
    image: ImageConfig
    appLogPrefix: str = "bk_paas3_app"
    ingressLogPrefix: str = "bk_paas3_ingress"


class BkAppLogCollectionValues(BaseModel):
    global_: BkAppLogCollectionGlobalValues = Field(alias="global")
    bkapp_filebeat: BkAppFilebeatValues = Field(alias="bkapp-filebeat")
    bkapp_logstash: BkAppLogstashValues = Field(alias="bkapp-logstash")


class BkPaaSAppOperatorValues(BaseModel):
    image: ImageConfig
    proxyImage: ImageConfig
