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


class ValuesConstructor(abc.ABC):
    """Chart values 构造器"""

    @abc.abstractmethod
    def construct(self) -> Dict[str, Any]:
        """生成特殊指定的 values（部署与默认配置合并 & 覆盖）"""
        ...


def get_values_constructor_cls(name: str) -> Type[ValuesConstructor]:
    if name == ClusterComponentName.BK_INGRESS_NGINX:
        return BkIngressNginxValuesConstructor

    if name == ClusterComponentName.BKAPP_LOG_COLLECTION:
        return BkAppLogCollectionValuesConstructor

    if name == ClusterComponentName.BKPAAS_APP_OPERATOR:
        return BkPaaSAppOperatorValuesConstructor

    return DefaultValuesConstructor


class DefaultValuesConstructor(ValuesConstructor):
    """默认：使用 Chart 默认 values，无需额外追加"""

    def __init__(self, *args, **kwargs): ...

    def construct(self) -> Dict[str, Any]:
        return {}


class BkIngressNginxValuesConstructor(ValuesConstructor):
    """bk-ingress-nginx 需要使用用户填写的配置"""

    def __init__(self, cluster_name: str, values: Dict[str, Any]):
        """
        :param values: 用户配置的 values
        """
        self.values = values

    def construct(self) -> Dict[str, Any]:
        return self.values


class BkAppLogCollectionValuesConstructor(ValuesConstructor):
    """bkapp-log-collection 使用 DB 中的配置"""

    def __init__(self, *args, **kwargs): ...

    def construct(self) -> Dict[str, Any]:
        return {}


class BkPaaSAppOperatorValuesConstructor(ValuesConstructor):
    """bkpaas-app-operator 使用 Chart 默认配置，只需设置镜像信息"""

    def __init__(self, *args, **kwargs): ...

    def construct(self) -> Dict[str, Any]:
        return {}
