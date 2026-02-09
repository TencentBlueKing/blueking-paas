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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

# 为方便用户填写而设计的端口占位符, 并非实际的 shell 环境变量. 在转换成 BkApp 模型时会被平台替换成预设值 settings.CONTAINER_PORT
PORT_PLACEHOLDER = "${PORT}"

# Maximum resource limitations for each process
# The same with the limitations in the Operator.
MAX_PROC_CPU = "48000m"
MAX_PROC_MEM = "65536Mi"


class ExposedTypeName(StrStructuredEnum):
    """与 paas_wl.workloads.networking.constants.ExposedTypeName 重复定义
    # TODO 将 paasng 和 paas_wl 中重复定义的一些常量, 合并放到更底层的模块中, 避免破坏当前 importlinter 的依赖规则?
    """

    BK_HTTP = "bk/http"
    BK_GRPC = "bk/grpc"


class NetworkProtocol(StrStructuredEnum):
    """与 paas_wl.workloads.networking.constants.NetworkProtocol 重复定义
    # TODO 将 paasng 和 paas_wl 中重复定义的一些常量, 合并放到更底层的模块中, 避免破坏当前 importlinter 的依赖规则?
    """

    TCP = EnumField("TCP", label="TCP")
    UDP = EnumField("UDP", label="UDP")


class ImagePullPolicy(StrStructuredEnum):
    """duplicated from paas_wl.workloads.release_controller.constants.ImagePullPolicy to decouple dependencies
    TODO 统一放置到一个独立于 paas_wl 和 paasng 的模块下?
    """

    ALWAYS = EnumField("Always")
    IF_NOT_PRESENT = EnumField("IfNotPresent")
    NEVER = EnumField("Never")


class ScalingPolicy(StrStructuredEnum):
    """duplicated from paas_wl.bk_app.cnative.specs.constants.ScalingPolicy to decouple dependencies
    TODO 统一放置到一个独立于 paas_wl 和 paasng 的模块下?
    """

    # the default autoscaling policy (cpu utilization 85%)
    DEFAULT = EnumField("default")


class CPUResourceQuantity(StrStructuredEnum):
    QUOTA_0_0_5_CORE = EnumField("50m", label="0.05 核")
    QUOTA_0_1_CORE = EnumField("100m", label="0.1 核")
    QUOTA_0_2_CORE = EnumField("200m", label="0.2 核")
    QUOTA_0_5_CORE = EnumField("500m", label="0.5 核")
    QUOTA_1_CORE = EnumField("1000m", label="1 核")
    QUOTA_2_CORE = EnumField("2000m", label="2 核")
    QUOTA_4_CORE = EnumField("4000m", label="4 核")
    QUOTA_8_CORE = EnumField("8000m", label="8 核")
    QUOTA_16_CORE = EnumField("16000m", label="16 核")

    def exceeds(self, other: "CPUResourceQuantity") -> bool:
        """检查当前资源值是否大于另一个资源值"""
        # 枚举值的顺序即为资源大小的顺序
        order = list(CPUResourceQuantity)
        return order.index(self) > order.index(other)


class MemoryResourceQuantity(StrStructuredEnum):
    QUOTA_256_M = EnumField("256Mi", label="256 Mi")
    QUOTA_512_M = EnumField("512Mi", label="512 Mi")
    QUOTA_1_G = EnumField("1024Mi", label="1 Gi")
    QUOTA_2_G = EnumField("2048Mi", label="2 Gi")
    QUOTA_4_G = EnumField("4096Mi", label="4 Gi")
    QUOTA_8_G = EnumField("8192Mi", label="8 Gi")
    QUOTA_16_G = EnumField("16384Mi", label="16 Gi")
    QUOTA_32_G = EnumField("32768Mi", label="32 Gi")

    def exceeds(self, other: "MemoryResourceQuantity") -> bool:
        """检查当前资源值是否大于另一个资源值"""
        # 枚举值的顺序即为资源大小的顺序
        order = list(MemoryResourceQuantity)
        return order.index(self) > order.index(other)
