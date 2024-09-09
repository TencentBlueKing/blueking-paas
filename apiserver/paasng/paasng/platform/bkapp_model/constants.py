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

from blue_krill.data_types.enum import EnumField, StructuredEnum

# legacy: Slug runner 默认的 entrypoint, 平台所有 slug runner 镜像都以该值作为入口
# TODO: 需验证存量所有镜像是否都设置了默认的 entrypoint, 如是, 即可移除所有 DEFAULT_SLUG_RUNNER_ENTRYPOINT
DEFAULT_SLUG_RUNNER_ENTRYPOINT = ["bash", "/runner/init"]

# 为方便用户填写而设计的端口占位符, 并非实际的 shell 环境变量. 在转换成 BkApp 模型时会被平台替换成预设值 settings.CONTAINER_PORT
PORT_PLACEHOLDER = "${PORT}"


class ExposedTypeName(str, StructuredEnum):
    """与 paas_wl.workloads.networking.constants.ExposedTypeName 重复定义
    # TODO 将 paasng 和 paas_wl 中重复定义的一些常量, 合并放到更底层的模块中, 避免破坏当前 importlinter 的依赖规则?
    """

    BK_HTTP = "bk/http"


class NetworkProtocol(str, StructuredEnum):
    """与 paas_wl.workloads.networking.constants.NetworkProtocol 重复定义
    # TODO 将 paasng 和 paas_wl 中重复定义的一些常量, 合并放到更底层的模块中, 避免破坏当前 importlinter 的依赖规则?
    """

    TCP = EnumField("TCP", label="TCP")
    UDP = EnumField("UDP", label="UDP")


class ImagePullPolicy(str, StructuredEnum):
    """duplicated from paas_wl.workloads.release_controller.constants.ImagePullPolicy to decouple dependencies
    TODO 统一放置到一个独立于 paas_wl 和 paasng 的模块下?
    """

    ALWAYS = EnumField("Always")
    IF_NOT_PRESENT = EnumField("IfNotPresent")
    NEVER = EnumField("Never")


class ResQuotaPlan(str, StructuredEnum):
    """duplicated from paas_wl.bk_app.cnative.specs.constants.ResQuotaPlan to decouple dependencies
    TODO 统一放置到一个独立于 paas_wl 和 paasng 的模块下?
    """

    P_DEFAULT = EnumField("default", label="default")
    P_4C1G = EnumField("4C1G", label="4C1G")
    P_4C2G = EnumField("4C2G", label="4C2G")
    P_4C4G = EnumField("4C4G", label="4C4G")

    # simulate `ReprEnum` behavior to work well with DRF serializer
    # see also:
    # - https://docs.python.org/3/library/enum.html#enum.ReprEnum
    # - https://docs.python.org/3/library/enum.html#enum.Enum.__str__
    __str__ = str.__str__


class ScalingPolicy(str, StructuredEnum):
    """duplicated from paas_wl.bk_app.cnative.specs.constants.ScalingPolicy to decouple dependencies
    TODO 统一放置到一个独立于 paas_wl 和 paasng 的模块下?
    """

    # the default autoscaling policy (cpu utilization 85%)
    DEFAULT = EnumField("default")

    # simulate `ReprEnum` behavior to work well with DRF serializer
    # see also:
    # - https://docs.python.org/3/library/enum.html#enum.ReprEnum
    # - https://docs.python.org/3/library/enum.html#enum.Enum.__str__
    __str__ = str.__str__
