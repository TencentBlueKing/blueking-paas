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

from paasng.platform.bkapp_model.constants import CPUResourceQuantity, MemoryResourceQuantity
from paasng.utils.structure import prepare_json_field


class ResourceQuantity(BaseModel):
    """
    资源数量模型，用于表示CPU和内存的具体数值及单位

    :param cpu: CPU 资源量，单位为 m
    :param memory: 内存资源量，单位为 Mi
    """

    cpu: str
    memory: str


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
            # 调用静态方法计算CPU和内存请求值
            cpu_requests = calculate_cpu_request(self.limits.cpu)
            memory_requests = calculate_memory_request(self.limits.memory)
            self.requests = ResourceQuantity(cpu=str(cpu_requests), memory=str(memory_requests))


def calculate_cpu_request(cpu_limit: int | str) -> int:
    """
    根据 CPU limits 计算 requests

    :param cpu_limit: CPU 限制值（原始数值或字符串）
    :return: 计算后的 CPU 请求值
    """
    # 如果是字符串，转换为整数
    if isinstance(cpu_limit, str):
        cpu_limit = int(cpu_limit)
    # 规则：CPU请求为 min(limits.cpu, 200)
    return min(cpu_limit, 200)


def calculate_memory_request(memory_limit: int | str) -> int:
    """
    根据内存 limits 计算 requests

    :param memory_limit: 内存限制值（原始数值或字符串，单位：Mi）
    :return: 计算后的内存请求值
    """
    # 如果是字符串，转换为整数
    if isinstance(memory_limit, str):
        memory_limit = int(memory_limit)
    # 规则：当 Limits >= 2048 Mi 时，值为 Limits 的 1/2；否则为 Limits 的 1/4
    if memory_limit >= 2048:
        return memory_limit // 2
    return memory_limit // 4


def get_cpu_recommend_resources() -> list:
    """获取 CPU 推荐资源配置"""
    cpu_list = []
    for item in CPUResourceQuantity.get_choices():
        value = item[0]
        label = item[1]
        request_value = calculate_cpu_request(value)
        request_label = f"{request_value / 1000} 核"
        cpu_list.append(
            {"limit": {"value": value, "label": label}, "request": {"value": request_value, "label": request_label}}
        )
    return cpu_list


def get_memory_recommend_resources() -> list:
    """获取内存推荐资源配置"""
    memory_list = []
    for item in MemoryResourceQuantity.get_choices():
        value = item[0]
        label = item[1]
        request_value = calculate_memory_request(value)
        if request_value >= 1024:
            request_label = f"{request_value // 1024} G"
        else:
            request_label = f"{request_value} M"
        memory_list.append(
            {"limit": {"value": value, "label": label}, "request": {"value": request_value, "label": request_label}}
        )
    return memory_list
