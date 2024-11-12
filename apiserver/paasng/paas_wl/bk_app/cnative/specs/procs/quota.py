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

from attrs import define

from paas_wl.bk_app.cnative.specs.constants import (
    DEFAULT_PROC_CPU,
    DEFAULT_PROC_CPU_REQUEST,
    DEFAULT_PROC_MEM,
    DEFAULT_PROC_MEM_REQUEST,
    ResQuotaPlan,
)


@define
class ResourceQuota:
    cpu: str
    memory: str


# 资源配额方案到资源限制的映射表
PLAN_TO_LIMIT_QUOTA_MAP = {
    ResQuotaPlan.P_DEFAULT: ResourceQuota(
        cpu=DEFAULT_PROC_CPU,
        memory=DEFAULT_PROC_MEM,
    ),
    ResQuotaPlan.P_4C1G: ResourceQuota(cpu="4000m", memory="1024Mi"),
    ResQuotaPlan.P_4C2G: ResourceQuota(cpu="4000m", memory="2048Mi"),
    ResQuotaPlan.P_4C4G: ResourceQuota(cpu="4000m", memory="4096Mi"),
}

# 资源配额方案到资源请求的映射表
# CPU REQUEST = 200m
# MEMORY REQUEST 的计算规则: 当 Limits 大于等于 2048 Mi 时，值为 Limits 的 1/2; 当 Limits 小于 2048 Mi 时，值为 Limits 的 1/4
# 云原生应用实际的 requests 配置策略在 operator 中实现, 这里的值并非实际生效值
PLAN_TO_REQUEST_QUOTA_MAP = {
    ResQuotaPlan.P_DEFAULT: ResourceQuota(
        cpu=DEFAULT_PROC_CPU_REQUEST,
        memory=DEFAULT_PROC_MEM_REQUEST,
    ),
    ResQuotaPlan.P_4C1G: ResourceQuota(cpu="200m", memory="256Mi"),
    ResQuotaPlan.P_4C2G: ResourceQuota(cpu="200m", memory="1024Mi"),
    ResQuotaPlan.P_4C4G: ResourceQuota(cpu="200m", memory="2048Mi"),
}
