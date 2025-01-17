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
from paasng.plat_mgt.infras.clusters.entities import HelmRelease
from paasng.plat_mgt.infras.clusters.values.entities import (
    BCSGPAValues,
    BkAppLogCollectionValues,
    BkIngressNginxValues,
    BkPaaSAppOperatorValues,
)


class ValuesGetter(abc.ABC):
    def __init__(self, release: HelmRelease):
        self.release = release

    def raw(self) -> Dict[str, Any]:
        return self.release.values

    @abc.abstractmethod
    def get(self) -> Dict[str, Any]: ...


def get_values_getter_cls(name: str) -> Type[ValuesGetter]:
    if name == ClusterComponentName.BK_INGRESS_NGINX:
        return BkIngressNginxValuesGetter

    if name == ClusterComponentName.BKAPP_LOG_COLLECTION:
        return BkAppLogCollectionValuesGetter

    if name == ClusterComponentName.BKPAAS_APP_OPERATOR:
        return BkPaaSAppOperatorValuesGetter

    if name == ClusterComponentName.BCS_GENERAL_POD_AUTOSCALER:
        return BCSGPAValuesGetter

    return DefaultValuesGetter


class DefaultValuesGetter(ValuesGetter):
    """默认：全量返回 Release 使用的 values"""

    def get(self) -> Dict[str, Any]:
        return self.raw()


class BkIngressNginxValuesGetter(ValuesGetter):
    """bk-ingress-nginx"""

    def get(self) -> Dict[str, Any]:
        values = BkIngressNginxValues(**self.release.values)
        return values.dict(by_alias=True)


class BkAppLogCollectionValuesGetter(ValuesGetter):
    """bkapp-log-collection"""

    def get(self) -> Dict[str, Any]:
        values = BkAppLogCollectionValues(**self.release.values)
        return values.dict(by_alias=True)


class BkPaaSAppOperatorValuesGetter(ValuesGetter):
    """bkpaas-app-operator"""

    def get(self) -> Dict[str, Any]:
        values = BkPaaSAppOperatorValues(**self.release.values)
        return values.dict(by_alias=True)


class BCSGPAValuesGetter(ValuesGetter):
    """bcs-general-pod-autoscaler"""

    def get(self) -> Dict[str, Any]:
        values = BCSGPAValues(**self.release.values)
        return values.dict(by_alias=True)
