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

import logging

from pydantic import BaseModel

from .scaling_config import AutoscalingConfig

logger = logging.getLogger(__name__)


class ResQuotaOverlay(BaseModel):
    """
    资源配额 Overlay

    :param env_name: 生效环境名
    :param process: 进程名称
    :param plan: 资源配额套餐名称
    """

    env_name: str
    process: str
    plan: str


class ReplicasOverlay(BaseModel):
    """
    副本数 Overlay

    :param env_name: 生效环境名
    :param process: 进程名称
    :param count: 副本数
    """

    env_name: str
    process: str
    count: int


class AutoscalingOverlay(AutoscalingConfig):
    """
    自动扩缩容 Overlay

    :param env_name: 生效环境名
    :param process: 进程名称
    """

    env_name: str
    process: str
