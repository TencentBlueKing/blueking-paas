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

from pydantic import BaseModel

from paasng.utils.structure import prepare_json_field


class ResourceQuantity(BaseModel):
    """
    资源数量模型，用于表示CPU和内存的具体数值及单位

    :param cpu: CPU 资源量，单位为 m
    :param memory: 内存资源量，单位为 Mi
    """

    cpu: int
    memory: int


@prepare_json_field
class Resources(BaseModel):
    """
    进程资源配置，包含资源限制和资源请求

    :param limits: 资源限制配置，指定容器可以使用的最大资源量
    :param requests: 资源请求配置，指定容器需要的最小资源量
    """

    limits: ResourceQuantity
    requests: ResourceQuantity | None = None

    def __init__(self, **data):
        # 如果未配置 requests，按照规则自动计算，规则与 Operator 保持一致
        # 目前 Requests 配额策略：CPU 为 min(limits.cpu, 200)，内存按照以下规则计算:
        # 当 Limits 大于等于 2048 Mi 时，值为 Limits 的 1/2; 当 Limits 小于 2048 Mi 时，值为 Limits 的 1/4
        super().__init__(**data)
        if self.requests is None:
            # 获取limits原始数据（可能是字典或ResourceQuantity实例
            cpu_requests = min(self.limits.cpu, 200)

            # 内存根据 limits 计算
            memory_limits = self.limits.memory
            if memory_limits >= 2048:
                memory_requests = memory_limits // 2
            else:
                memory_requests = memory_limits // 4

            self.requests = ResourceQuantity(cpu=cpu_requests, memory=memory_requests)
