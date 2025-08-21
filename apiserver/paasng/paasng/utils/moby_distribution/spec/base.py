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

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Platform(BaseModel):
    """
    Platform describes the platform which the image in the manifest runs on.
    """

    architecture: str
    os: str
    os_version: str = Field(alias="os.version")
    os_features: Optional[List[str]] = Field(alias="os.features")
    variant: str


class Descriptor(BaseModel):
    """
    Descriptor describes targeted content. Used in conjunction with a blob
    store, a descriptor can be used to fetch, store and target any kind of
    blob. The struct also describes the wire protocol format. Fields should
    only be added but never changed.

    spec: https://github.com/distribution/distribution/blob/cc4627fc6e5f20cfe8534492b44331fa16ccf872/blobs.go#L61
    see also: https://github.com/opencontainers/image-spec/blob/main/descriptor.md
    """

    mediaType: str
    size: int
    digest: str
    urls: List[str] = Field(default_factory=list)
    annotations: Dict[str, str] = Field(default_factory=dict)
    platform: Optional[Platform] = None
