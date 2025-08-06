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

from typing import Any, Dict, Type

from pydantic import BaseModel

from paas_wl.infras.cluster.constants import ClusterComponentName
from paas_wl.infras.cluster.entities import HelmRelease
from paasng.plat_mgt.infras.clusters.values.entities import (
    BCSGPAValues,
    BkAppLogCollectionValues,
    BkIngressNginxValues,
    BkPaaSAppOperatorValues,
)


class UserValuesGetter:
    """获取简化后的 values（用户指定的）"""

    def __init__(self, release: HelmRelease):
        self.release = release
        self.values_model = get_values_model(release.name)

    def get(self) -> Dict[str, Any]:
        values = self.release.values

        if not self.values_model:
            return values

        return self.values_model(**values).dict(by_alias=True)


def get_values_model(name: str) -> Type[BaseModel] | None:
    match name:
        case ClusterComponentName.BK_INGRESS_NGINX:
            return BkIngressNginxValues

        case ClusterComponentName.BKAPP_LOG_COLLECTION:
            return BkAppLogCollectionValues

        case ClusterComponentName.BKPAAS_APP_OPERATOR:
            return BkPaaSAppOperatorValues

        case ClusterComponentName.BCS_GENERAL_POD_AUTOSCALER:
            return BCSGPAValues

    return None
