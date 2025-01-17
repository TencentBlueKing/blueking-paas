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

import abc
from typing import Any, Dict, Type

from paas_wl.infras.cluster.constants import ClusterComponentName
from paas_wl.infras.cluster.models import Cluster, ClusterElasticSearchConfig
from paasng.plat_mgt.infras.clusters.values.entities import (
    BCSGPAValues,
    BkAppLogCollectionValues,
    BkIngressNginxValues,
    BkPaaSAppOperatorValues,
)


class ValuesConstructor(abc.ABC):
    """Chart values 构造器"""

    def __init__(self, cluster: Cluster):
        self.cluster = cluster

    @abc.abstractmethod
    def construct(self, user_values: Dict[str, Any]) -> Dict[str, Any]:
        """生成特殊指定的 values（部署与默认配置合并 & 覆盖）"""
        ...


def get_values_constructor_cls(name: str) -> Type[ValuesConstructor]:
    if name == ClusterComponentName.BK_INGRESS_NGINX:
        return BkIngressNginxValuesConstructor

    if name == ClusterComponentName.BKAPP_LOG_COLLECTION:
        return BkAppLogCollectionValuesConstructor

    if name == ClusterComponentName.BKPAAS_APP_OPERATOR:
        return BkPaaSAppOperatorValuesConstructor

    if name == ClusterComponentName.BCS_GENERAL_POD_AUTOSCALER:
        return BCSGPAValuesConstructor

    return DefaultValuesConstructor


class DefaultValuesConstructor(ValuesConstructor):
    """默认：直接使用用户提供的 values"""

    def construct(self, user_values: Dict[str, Any]) -> Dict[str, Any]:
        return user_values


class BkIngressNginxValuesConstructor(ValuesConstructor):
    """bk-ingress-nginx 需要使用用户填写的配置"""

    def construct(self, user_values: Dict[str, Any]) -> Dict[str, Any]:
        values = BkIngressNginxValues(**user_values)
        # 覆盖默认的镜像源地址
        values.image.registry = self.cluster.component_image_registry
        return values.dict(by_alias=True)


class BkAppLogCollectionValuesConstructor(ValuesConstructor):
    """bkapp-log-collection 使用 DB 中的配置"""

    def construct(self, user_values: Dict[str, Any]) -> Dict[str, Any]:
        # 从数据库中获取 ES 集群配置
        es_cfg = ClusterElasticSearchConfig.objects.filter(cluster=self.cluster).first()
        if not es_cfg:
            raise ValueError("elastic search config for cluster %s not found" % self.cluster.name)

        raw_values = {
            "global": {
                "elasticSearchUsername": es_cfg.username,
                "elasticSearchPassword": es_cfg.password,
                "elasticSearchScheme": es_cfg.scheme,
                "elasticSearchHost": es_cfg.host,
                "elasticSearchPort": es_cfg.port,
            },
            "bkapp-filebeat": {
                "image": {
                    "registry": self.cluster.component_image_registry,
                },
            },
            "bkapp-logstash": {
                "image": {
                    "registry": self.cluster.component_image_registry,
                },
            },
        }
        values = BkAppLogCollectionValues(**raw_values)
        return values.dict(by_alias=True)


class BkPaaSAppOperatorValuesConstructor(ValuesConstructor):
    """bkpaas-app-operator 使用 Chart 默认配置，只需设置镜像源信息"""

    def construct(self, user_values: Dict[str, Any]) -> Dict[str, Any]:
        # 覆盖默认的镜像源地址
        raw_values = {
            "image": {
                "registry": self.cluster.component_image_registry,
            },
            "proxyImage": {
                "registry": self.cluster.component_image_registry,
            },
        }
        values = BkPaaSAppOperatorValues(**raw_values)
        return values.dict(by_alias=True)


class BCSGPAValuesConstructor(ValuesConstructor):
    """bcs-general-pod-autoscaler 使用 Chart 默认配置，只需设置镜像源信息"""

    def construct(self, user_values: Dict[str, Any]) -> Dict[str, Any]:
        # 覆盖默认的镜像源地址
        raw_values = {
            "image": {
                "registry": self.cluster.component_image_registry,
            }
        }
        values = BCSGPAValues(**raw_values)
        return values.dict(by_alias=True)
