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

from datetime import datetime
from typing import Any, Dict, List

from attr import define

from paasng.plat_mgt.infras.clusters.constants import HelmChartDeployStatus


@define
class DeployResult:
    # 部署状态
    status: HelmChartDeployStatus
    # 部署详情
    description: str
    # 部署时间
    created_at: datetime


@define
class HelmChart:
    # Chart 名称
    name: str
    # Chart 版本
    version: str
    # App 版本
    app_version: str
    # Chart 描述
    description: str


@define
class HelmRelease:
    # release 名称
    name: str
    # 部署的命名空间
    namespace: str
    # release 版本
    version: int
    # chart 信息
    chart: HelmChart
    # 部署信息
    deploy_result: DeployResult
    # 部署配置信息
    values: Dict
    # 部署的 k8s 资源信息
    resources: List[Dict[str, Any]]
    # 存储 release secret 名称
    secret_name: str
