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

from typing import Optional

from pydantic import BaseModel


class ConfigMapSource(BaseModel):
    name: str


class PersistentStorage(BaseModel):
    name: str


class VolumeSource(BaseModel):
    config_map: Optional[ConfigMapSource] = None
    persistent_storage: Optional[PersistentStorage] = None


class Mount(BaseModel):
    """
    Mount

    :param mount_path: 挂载路径
    :param name: 挂载名称
    :param source: 挂载源
    """

    mount_path: str
    name: str
    source: VolumeSource


class MountOverlay(Mount):
    """
    Mount Overlay

    :param env_name: 生效环境名
    """

    env_name: str
