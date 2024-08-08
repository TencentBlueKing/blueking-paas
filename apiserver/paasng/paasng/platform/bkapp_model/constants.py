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


class ImagePullPolicy(str, StructuredEnum):
    """duplicated from paas_wl.workloads.release_controller.constants.ImagePullPolicy to decouple dependencies"""

    ALWAYS = EnumField("Always")
    IF_NOT_PRESENT = EnumField("IfNotPresent")
    NEVER = EnumField("Never")


class ResQuotaPlan(str, StructuredEnum):
    """duplicated from paas_wl.bk_app.cnative.specs.constants.ResQuotaPlan to decouple dependencies"""

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
    """duplicated from paas_wl.bk_app.cnative.specs.constants.ScalingPolicy to decouple dependencies"""

    # the default autoscaling policy (cpu utilization 85%)
    DEFAULT = EnumField("default")

    # simulate `ReprEnum` behavior to work well with DRF serializer
    # see also:
    # - https://docs.python.org/3/library/enum.html#enum.ReprEnum
    # - https://docs.python.org/3/library/enum.html#enum.Enum.__str__
    __str__ = str.__str__
