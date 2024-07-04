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

"""Kubernetes API related utilities"""
from typing import Dict

from pydantic import BaseModel, Field

from paas_wl.utils.text import DNS_SAFE_PATTERN


class ObjectMetadata(BaseModel):
    """Kubernetes Metadata"""

    # See https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    name: str = Field(..., regex=DNS_SAFE_PATTERN, max_length=253)
    annotations: Dict[str, str] = Field(default_factory=dict)
    generation: int = Field(default=0)
