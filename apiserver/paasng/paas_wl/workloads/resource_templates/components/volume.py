# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import List, Optional

from attrs import define, field


@define
class VolumeMount:
    name: str
    mountPath: str
    readOnly: bool = False
    mountPropagation: Optional[str] = None
    subPath: Optional[str] = None
    # k8s 1.8 不支持该字段
    # subPathExpr: Optional[str] = None


@define
class KeyToPath:
    key: str
    path: str
    mode: int = 0o644


@define
class EmptyDirVolumeSource:
    medium: Optional[str] = None
    sizeLimit: Optional[str] = None


@define
class HostPathVolumeSource:
    path: str
    type: Optional[str] = None


@define
class SecretVolumeSource:
    secretName: str
    items: List[KeyToPath] = field(factory=list)
    optional: bool = False
    defaultMode: int = 0o644


@define
class Volume:
    name: str
    emptyDir: Optional[EmptyDirVolumeSource] = None
    hostPath: Optional[HostPathVolumeSource] = None
    secret: Optional[SecretVolumeSource] = None
